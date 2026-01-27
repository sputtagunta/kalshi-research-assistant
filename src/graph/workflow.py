"""
LangGraph Workflow for Kalshi Research

Defines the research workflow as a directed acyclic graph with:
- Strict linear execution
- State validation guards between nodes
- Error handling and recovery
"""

from typing import Optional
from anthropic import Anthropic

from .state import KalshiResearchState
from .nodes import (
    market_ingestor_node,
    market_parser_node,
    independent_researcher_node,
    probability_estimator_node,
    mispricing_analyst_node,
    persona_recommender_node,
    scenario_analyst_node,
    final_suggester_node,
)
from .validators import ValidationError


# Default personas
DEFAULT_PERSONAS = [
    "risk_averse",
    "risk_seeking",
    "news_driven",
    "macro_thinker",
    "casual_participant",
    "data_analyst",
]


class ResearchWorkflow:
    """
    Orchestrates the Kalshi research workflow.

    Execution order:
    1. market_ingestor - Validate user input
    2. market_parser - Extract market mechanics
    3. independent_researcher - Gather external research
    4. probability_estimator - Form independent estimates
    5. mispricing_analyst - Compare to market pricing
    6. persona_recommender - Generate persona suggestions
    7. scenario_analyst - Stress test the thesis
    8. final_suggester - Synthesize final report
    """

    def __init__(
        self,
        client: Optional[Anthropic] = None,
        personas: Optional[list[str]] = None,
        verbose: bool = True
    ):
        self.client = client or Anthropic()
        self.personas = personas or DEFAULT_PERSONAS
        self.verbose = verbose

        # Define workflow steps
        self.steps = [
            ("market_ingestor", market_ingestor_node),
            ("market_parser", market_parser_node),
            ("independent_researcher", independent_researcher_node),
            ("probability_estimator", probability_estimator_node),
            ("mispricing_analyst", mispricing_analyst_node),
            ("persona_recommender", lambda s, c: persona_recommender_node(s, c, self.personas)),
            ("scenario_analyst", scenario_analyst_node),
            ("final_suggester", lambda s, c: final_suggester_node(s, c, self.personas)),
        ]

    def _log(self, message: str) -> None:
        """Print message if verbose mode is enabled."""
        if self.verbose:
            print(message)

    def run(self, market_input: str) -> KalshiResearchState:
        """
        Execute the full research workflow.

        Args:
            market_input: User-provided Kalshi market (URL, ID, or description)

        Returns:
            KalshiResearchState with completed analysis
        """
        state = KalshiResearchState(user_market_input=market_input)

        self._log(f"\n{'='*60}")
        self._log("Kalshi Research Workflow Starting")
        self._log(f"{'='*60}\n")

        for step_name, node_func in self.steps:
            self._log(f"[{step_name}] Running...")

            try:
                state = node_func(state, self.client)

                # Check for validation errors that should stop the workflow
                if state.input_validation_error and step_name == "market_ingestor":
                    self._log(f"[{step_name}] Validation failed: {state.input_validation_error}")
                    return state

                # Check for critical errors
                if state.errors and len(state.errors) > len([e for e in state.errors if "Warning" in e]):
                    critical_errors = [e for e in state.errors if "Warning" not in e]
                    if critical_errors:
                        self._log(f"[{step_name}] Error: {critical_errors[-1]}")

                self._log(f"[{step_name}] Complete")

            except Exception as e:
                error_msg = f"Step {step_name} failed: {str(e)}"
                state.errors.append(error_msg)
                self._log(f"[{step_name}] FAILED: {e}")

                # Continue to next step if possible, or abort for critical failures
                if step_name in ("market_ingestor", "market_parser"):
                    self._log("Critical step failed - aborting workflow")
                    break

        self._log(f"\n{'='*60}")
        self._log("Workflow Complete")
        self._log(f"{'='*60}\n")

        return state

    def run_step(self, state: KalshiResearchState, step_name: str) -> KalshiResearchState:
        """
        Run a single workflow step.

        Args:
            state: Current workflow state
            step_name: Name of the step to run

        Returns:
            Updated state
        """
        for name, node_func in self.steps:
            if name == step_name:
                return node_func(state, self.client)

        raise ValueError(f"Unknown step: {step_name}")


def create_research_workflow(
    client: Optional[Anthropic] = None,
    personas: Optional[list[str]] = None,
    verbose: bool = True
) -> ResearchWorkflow:
    """
    Factory function to create a research workflow.

    Args:
        client: Anthropic client (creates new one if not provided)
        personas: List of persona names to generate recommendations for
        verbose: Whether to print progress messages

    Returns:
        Configured ResearchWorkflow instance
    """
    return ResearchWorkflow(client=client, personas=personas, verbose=verbose)


def run_research(
    market_input: str,
    client: Optional[Anthropic] = None,
    personas: Optional[list[str]] = None,
    verbose: bool = True
) -> KalshiResearchState:
    """
    Convenience function to run research on a market.

    Args:
        market_input: User-provided Kalshi market (URL, ID, or description)
        client: Anthropic client (creates new one if not provided)
        personas: List of persona names to generate recommendations for
        verbose: Whether to print progress messages

    Returns:
        KalshiResearchState with completed analysis
    """
    workflow = create_research_workflow(client=client, personas=personas, verbose=verbose)
    return workflow.run(market_input)
