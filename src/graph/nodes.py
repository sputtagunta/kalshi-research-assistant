"""
LangGraph Nodes for Kalshi Research Workflow

Each node:
- Calls one Claude skill
- Writes to specific state keys
- Validates inputs and outputs
"""

import json
import os
from pathlib import Path
from typing import Callable
from anthropic import Anthropic

from .state import KalshiResearchState
from .validators import (
    validate_user_input,
    validate_market_ingested,
    validate_market_parsed,
    validate_research_complete,
    validate_probabilities_estimated,
    validate_mispricing_analyzed,
    ValidationError,
)
from .kalshi_api import (
    extract_ticker_from_input,
    fetch_market,
    KalshiAPIError,
)


def load_skill(skill_name: str) -> str:
    """Load a Claude skill system prompt from .claude/skills/"""
    project_root = Path(__file__).parent.parent.parent
    skill_path = project_root / ".claude" / "skills" / f"{skill_name}.md"

    if not skill_path.exists():
        raise FileNotFoundError(f"Skill not found: {skill_path}")

    return skill_path.read_text()


def call_claude(system_prompt: str, user_message: str, client: Anthropic) -> str:
    """Call Claude with a skill prompt and return the response."""
    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=4096,
        system=system_prompt,
        messages=[{"role": "user", "content": user_message}]
    )
    return response.content[0].text


def parse_json_response(response: str) -> dict:
    """Extract JSON from Claude's response, handling markdown code blocks."""
    # Try to find JSON in code blocks first
    if "```json" in response:
        start = response.find("```json") + 7
        end = response.find("```", start)
        response = response[start:end].strip()
    elif "```" in response:
        start = response.find("```") + 3
        end = response.find("```", start)
        response = response[start:end].strip()

    try:
        return json.loads(response)
    except json.JSONDecodeError:
        # Try to find any JSON object in the response
        start = response.find("{")
        end = response.rfind("}") + 1
        if start != -1 and end != 0:
            return json.loads(response[start:end])
        raise ValueError(f"Could not parse JSON from response: {response[:200]}...")


def market_ingestor_node(state: KalshiResearchState, client: Anthropic) -> KalshiResearchState:
    """
    Node 1: Validate and normalize user-provided market input.

    Input: user_market_input
    Output: market_title, market_url_or_id, input_validation_error
    """
    state.current_step = "market_ingestor"

    try:
        validate_user_input(state)
    except ValidationError as e:
        state.input_validation_error = str(e)
        state.errors.append(str(e))
        return state

    skill_prompt = load_skill("market_ingestor")
    user_message = f"""Please analyze this Kalshi market input:

{state.user_market_input}

Return your analysis as JSON."""

    response = call_claude(skill_prompt, user_message, client)

    try:
        result = parse_json_response(response)

        if result.get("validation_status") == "valid":
            state.market_title = result.get("market_title")
            state.market_url_or_id = result.get("market_url_or_id")
        elif result.get("validation_status") == "needs_clarification":
            state.input_validation_error = result.get("validation_message", "Clarification needed")
        else:
            state.input_validation_error = result.get("validation_message", "Invalid market input")

    except (ValueError, KeyError) as e:
        state.input_validation_error = f"Failed to parse market: {e}"
        state.errors.append(str(e))

    return state


def market_parser_node(state: KalshiResearchState, client: Anthropic) -> KalshiResearchState:
    """
    Node 2: Parse market mechanics by fetching from Kalshi API.

    Input: market_title, market_url_or_id
    Output: resolution_criteria, expiration_date, market_odds
    """
    state.current_step = "market_parser"

    try:
        validate_market_ingested(state)
    except ValidationError as e:
        state.errors.append(str(e))
        return state

    # Try to extract ticker and fetch from Kalshi API
    ticker = extract_ticker_from_input(state.user_market_input)
    if not ticker and state.market_url_or_id:
        ticker = extract_ticker_from_input(state.market_url_or_id)

    if ticker:
        try:
            market_data = fetch_market(ticker)

            # Build resolution criteria from rules
            resolution_criteria = market_data.rules_primary
            if market_data.rules_secondary:
                resolution_criteria += f"\n\nAdditional terms: {market_data.rules_secondary}"

            state.resolution_criteria = resolution_criteria
            state.expiration_date = market_data.expiration_time
            state.market_title = market_data.title or state.market_title

            # Calculate implied probabilities from bid/ask midpoint
            yes_mid = (market_data.yes_bid + market_data.yes_ask) / 2 if market_data.yes_ask else market_data.last_price
            no_mid = (market_data.no_bid + market_data.no_ask) / 2 if market_data.no_ask else (1 - market_data.last_price)

            # Use last price as fallback
            if yes_mid == 0 and market_data.last_price:
                yes_mid = market_data.last_price
                no_mid = 1 - market_data.last_price

            state.market_odds = [
                {
                    "outcome": "Yes",
                    "implied_probability": round(yes_mid, 4),
                    "current_price": round(yes_mid, 4),
                },
                {
                    "outcome": "No",
                    "implied_probability": round(no_mid, 4),
                    "current_price": round(no_mid, 4),
                },
            ]

            return state

        except KalshiAPIError as e:
            state.errors.append(f"Kalshi API: {e}")
            # Fall through to Claude-based parsing as fallback

    # Fallback: Use Claude to parse (limited without API data)
    skill_prompt = load_skill("market_parser")
    user_message = f"""Please parse this Kalshi market:

Market Title: {state.market_title}
Market Reference: {state.market_url_or_id}
Original Input: {state.user_market_input}

Note: Unable to fetch live data from Kalshi API. Please extract what information
you can from the input, and clearly mark any fields that are unknown.
Return your analysis as JSON."""

    response = call_claude(skill_prompt, user_message, client)

    try:
        result = parse_json_response(response)
        state.resolution_criteria = result.get("resolution_criteria")
        state.expiration_date = result.get("expiration_date")
        state.market_odds = result.get("market_odds", [])
    except (ValueError, KeyError) as e:
        state.errors.append(f"Failed to parse market mechanics: {e}")

    return state


def independent_researcher_node(state: KalshiResearchState, client: Anthropic) -> KalshiResearchState:
    """
    Node 3: Conduct independent research.

    Input: market_title, resolution_criteria
    Output: research_summary, sources
    """
    state.current_step = "independent_researcher"

    try:
        validate_market_parsed(state)
    except ValidationError as e:
        state.errors.append(str(e))
        return state

    skill_prompt = load_skill("independent_researcher")
    user_message = f"""Please conduct independent research on this prediction market:

Market: {state.market_title}
Resolution Criteria: {state.resolution_criteria}
Expiration: {state.expiration_date}

Research the factors that could affect this outcome.
DO NOT reference any market prices in your research.
Return your findings as JSON."""

    response = call_claude(skill_prompt, user_message, client)

    try:
        result = parse_json_response(response)
        state.research_summary = result.get("research_summary")
        state.sources = result.get("sources", [])
    except (ValueError, KeyError) as e:
        state.errors.append(f"Failed to parse research: {e}")

    return state


def probability_estimator_node(state: KalshiResearchState, client: Anthropic) -> KalshiResearchState:
    """
    Node 4: Estimate probabilities based on research.

    Input: research_summary, sources
    Output: estimated_probabilities, confidence_level
    """
    state.current_step = "probability_estimator"

    try:
        validate_research_complete(state)
    except ValidationError as e:
        state.errors.append(str(e))
        return state

    # Get outcome names from parsed market odds
    outcomes = [odds["outcome"] for odds in state.market_odds] if state.market_odds else ["Yes", "No"]

    skill_prompt = load_skill("probability_estimator")
    user_message = f"""Based on this research, estimate probabilities for the market outcomes.

Market: {state.market_title}
Resolution Criteria: {state.resolution_criteria}

Possible Outcomes: {', '.join(outcomes)}

Research Summary:
{state.research_summary}

Sources consulted: {', '.join(state.sources)}

DO NOT look at or reference any market prices.
Form your probability estimates based ONLY on the research above.
Return your estimates as JSON."""

    response = call_claude(skill_prompt, user_message, client)

    try:
        result = parse_json_response(response)
        state.estimated_probabilities = result.get("estimated_probabilities", [])
        state.confidence_level = result.get("confidence_level")
    except (ValueError, KeyError) as e:
        state.errors.append(f"Failed to parse probability estimates: {e}")

    return state


def mispricing_analyst_node(state: KalshiResearchState, client: Anthropic) -> KalshiResearchState:
    """
    Node 5: Analyze mispricing between estimates and market.

    Input: estimated_probabilities, market_odds
    Output: pricing_comparison, edge_analysis
    """
    state.current_step = "mispricing_analyst"

    try:
        validate_probabilities_estimated(state)
    except ValidationError as e:
        state.errors.append(str(e))
        return state

    skill_prompt = load_skill("mispricing_analyst")

    # Format the comparison data
    estimates_str = json.dumps(state.estimated_probabilities, indent=2)
    market_str = json.dumps(state.market_odds, indent=2)

    user_message = f"""Compare these probability estimates to market pricing:

Market: {state.market_title}
Confidence Level: {state.confidence_level}

Your Independent Estimates:
{estimates_str}

Current Market Pricing:
{market_str}

Analyze where mispricing might exist.
Return your analysis as JSON."""

    response = call_claude(skill_prompt, user_message, client)

    try:
        result = parse_json_response(response)
        state.pricing_comparison = result.get("pricing_comparison", [])
        state.edge_analysis = result.get("edge_analysis")
    except (ValueError, KeyError) as e:
        state.errors.append(f"Failed to parse mispricing analysis: {e}")

    return state


def persona_recommender_node(state: KalshiResearchState, client: Anthropic, personas: list[str]) -> KalshiResearchState:
    """
    Node 6: Generate persona-specific recommendations.

    Input: pricing_comparison, edge_analysis
    Output: persona_recommendations
    """
    state.current_step = "persona_recommender"

    try:
        validate_mispricing_analyzed(state)
    except ValidationError as e:
        state.errors.append(str(e))
        return state

    skill_prompt = load_skill("persona_recommender")

    comparison_str = json.dumps(state.pricing_comparison, indent=2)

    user_message = f"""Generate persona-specific suggestions for this market analysis:

Market: {state.market_title}

Pricing Comparison:
{comparison_str}

Edge Analysis:
{state.edge_analysis}

Generate suggestions for these personas: {', '.join(personas)}

Return your suggestions as JSON."""

    response = call_claude(skill_prompt, user_message, client)

    try:
        result = parse_json_response(response)
        state.persona_recommendations = result.get("persona_recommendations", [])
    except (ValueError, KeyError) as e:
        state.errors.append(f"Failed to parse persona recommendations: {e}")

    return state


def scenario_analyst_node(state: KalshiResearchState, client: Anthropic) -> KalshiResearchState:
    """
    Node 7: Generate scenario analysis.

    Input: All prior analysis
    Output: scenarios
    """
    state.current_step = "scenario_analyst"

    if not state.persona_recommendations:
        state.errors.append("No persona recommendations - cannot proceed to scenarios")
        return state

    skill_prompt = load_skill("scenario_analyst")

    comparison_str = json.dumps(state.pricing_comparison, indent=2)

    user_message = f"""Generate scenario analysis for this market:

Market: {state.market_title}
Resolution: {state.resolution_criteria}
Expiration: {state.expiration_date}

Current Analysis:
{state.edge_analysis}

Pricing Comparison:
{comparison_str}

Generate best-case, worst-case, and most-likely scenarios.
Return your analysis as JSON."""

    response = call_claude(skill_prompt, user_message, client)

    try:
        result = parse_json_response(response)
        state.scenarios = result.get("scenarios", [])
    except (ValueError, KeyError) as e:
        state.errors.append(f"Failed to parse scenario analysis: {e}")

    return state


def final_suggester_node(state: KalshiResearchState, client: Anthropic, personas: list[str]) -> KalshiResearchState:
    """
    Node 8: Generate final research report.

    Input: All prior analysis
    Output: final_output
    """
    state.current_step = "final_suggester"

    # Validate all prerequisites
    from .validators import validate_ready_for_output
    try:
        validate_ready_for_output(state, personas)
    except ValidationError as e:
        # Continue anyway but note the issue
        state.errors.append(f"Warning: {e}")

    skill_prompt = load_skill("final_suggester")

    # Compile all analysis into the prompt
    user_message = f"""Synthesize this analysis into a final research report:

## Market Information
- Title: {state.market_title}
- Reference: {state.market_url_or_id}
- Resolution: {state.resolution_criteria}
- Expiration: {state.expiration_date}

## Current Market Pricing
{json.dumps(state.market_odds, indent=2)}

## Independent Research
{state.research_summary}

Sources: {', '.join(state.sources)}

## Probability Estimates
{json.dumps(state.estimated_probabilities, indent=2)}
Confidence: {state.confidence_level}

## Mispricing Analysis
{json.dumps(state.pricing_comparison, indent=2)}

Edge Analysis: {state.edge_analysis}

## Persona Recommendations
{json.dumps(state.persona_recommendations, indent=2)}

## Scenarios
{json.dumps(state.scenarios, indent=2)}

Generate the final report as JSON with a 'final_output' field containing markdown."""

    response = call_claude(skill_prompt, user_message, client)

    try:
        result = parse_json_response(response)
        state.final_output = result.get("final_output")
    except (ValueError, KeyError):
        # If JSON parsing fails, use the response directly if it looks like markdown
        if response.strip().startswith("#"):
            state.final_output = response
        else:
            state.errors.append("Failed to generate final report")

    state.current_step = "completed"
    return state


# Node factory for creating bound node functions
def create_node_runner(
    node_func: Callable,
    client: Anthropic,
    personas: list[str] = None
) -> Callable[[KalshiResearchState], KalshiResearchState]:
    """Create a node runner with bound client and personas."""

    def runner(state: KalshiResearchState) -> KalshiResearchState:
        if personas is not None and node_func in (persona_recommender_node, final_suggester_node):
            return node_func(state, client, personas)
        return node_func(state, client)

    return runner
