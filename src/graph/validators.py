"""
State Validators for Kalshi Research Workflow

Each validator ensures required upstream fields exist before a node can execute.
Validators fail fast if assumptions are missing.
"""

from .state import KalshiResearchState


class ValidationError(Exception):
    """Raised when state validation fails."""
    pass


def validate_user_input(state: KalshiResearchState) -> None:
    """Validate that user has provided market input."""
    if not state.user_market_input or not state.user_market_input.strip():
        raise ValidationError(
            "No market input provided. Please provide a Kalshi market URL, ID, or description."
        )


def validate_market_ingested(state: KalshiResearchState) -> None:
    """Validate that market has been successfully ingested."""
    if state.input_validation_error:
        raise ValidationError(
            f"Market input validation failed: {state.input_validation_error}"
        )
    if not state.market_title:
        raise ValidationError(
            "Market title not extracted. Cannot proceed without identified market."
        )


def validate_market_parsed(state: KalshiResearchState) -> None:
    """Validate that market mechanics have been parsed."""
    if not state.resolution_criteria:
        raise ValidationError(
            "Resolution criteria not extracted. Cannot research without knowing what resolves the market."
        )
    if not state.market_odds:
        raise ValidationError(
            "Market odds not extracted. Cannot proceed without current pricing."
        )


def validate_research_complete(state: KalshiResearchState) -> None:
    """Validate that independent research has been conducted."""
    if not state.research_summary:
        raise ValidationError(
            "Research summary missing. Cannot estimate probabilities without research."
        )
    if not state.sources:
        raise ValidationError(
            "No sources provided. Research must cite verifiable sources."
        )


def validate_probabilities_estimated(state: KalshiResearchState) -> None:
    """Validate probability estimates exist and are reasonable."""
    if not state.estimated_probabilities:
        raise ValidationError(
            "No probability estimates. Cannot analyze mispricing without estimates."
        )

    # Check probabilities sum to approximately 1 (within tolerance)
    total = sum(p["estimated_probability"] for p in state.estimated_probabilities)
    if not (0.95 <= total <= 1.05):
        raise ValidationError(
            f"Probability estimates sum to {total:.2f}, should be ~1.0. "
            "Please revise estimates to ensure they form a valid probability distribution."
        )

    if not state.confidence_level:
        raise ValidationError(
            "Confidence level not specified. Must indicate low/medium/high confidence."
        )


def validate_mispricing_analyzed(state: KalshiResearchState) -> None:
    """Validate mispricing analysis is complete."""
    if not state.pricing_comparison:
        raise ValidationError(
            "Pricing comparison missing. Cannot make recommendations without mispricing analysis."
        )
    if not state.edge_analysis:
        raise ValidationError(
            "Edge analysis missing. Must explain potential edges before recommendations."
        )


def validate_personas_covered(state: KalshiResearchState, required_personas: list[str]) -> None:
    """Validate all required personas have recommendations."""
    if not state.persona_recommendations:
        raise ValidationError(
            "No persona recommendations generated."
        )

    covered_personas = {r["persona"] for r in state.persona_recommendations}
    missing = set(required_personas) - covered_personas

    if missing:
        raise ValidationError(
            f"Missing recommendations for personas: {', '.join(missing)}"
        )


def validate_scenarios_complete(state: KalshiResearchState) -> None:
    """Validate scenario analysis is complete."""
    if not state.scenarios:
        raise ValidationError(
            "No scenarios generated. Must include best/worst/most-likely scenarios."
        )

    scenario_types = {s["type"] for s in state.scenarios}
    required_types = {"best_case", "worst_case", "most_likely"}
    missing = required_types - scenario_types

    if missing:
        raise ValidationError(
            f"Missing scenario types: {', '.join(missing)}"
        )


def validate_ready_for_output(state: KalshiResearchState, required_personas: list[str]) -> None:
    """Validate all prerequisites for final output are met."""
    validate_market_ingested(state)
    validate_market_parsed(state)
    validate_research_complete(state)
    validate_probabilities_estimated(state)
    validate_mispricing_analyzed(state)
    validate_personas_covered(state, required_personas)
    validate_scenarios_complete(state)
