"""
LangGraph State Definition for Kalshi Research Workflow

This module defines the typed state object that flows through the research pipeline.
Each field must be explicitly written before downstream access.
"""

from typing import TypedDict, Optional
from dataclasses import dataclass, field


class MarketOdds(TypedDict):
    """Represents odds for a single outcome."""
    outcome: str
    implied_probability: float
    current_price: Optional[float]


class ProbabilityEstimate(TypedDict):
    """Represents an estimated probability for an outcome."""
    outcome: str
    estimated_probability: float
    reasoning: str


class PricingComparison(TypedDict):
    """Comparison between estimated and market probabilities."""
    outcome: str
    market_probability: float
    estimated_probability: float
    difference: float
    assessment: str  # "overpriced", "underpriced", "fairly_priced"


class PersonaRecommendation(TypedDict):
    """Recommendation tailored to a specific persona."""
    persona: str
    suggested_position: str
    rationale: str
    key_risks: list[str]


class Scenario(TypedDict):
    """A scenario analysis."""
    type: str  # "best_case", "worst_case", "most_likely"
    description: str
    probability_shift: str
    key_triggers: list[str]


@dataclass
class KalshiResearchState:
    """
    Immutable state object passed between LangGraph nodes.

    Flow:
    1. user_market_input -> market_ingestor
    2. market_title, market_url_or_id -> market_parser
    3. resolution_criteria, expiration_date, market_odds -> independent_researcher
    4. research_summary, sources -> probability_estimator
    5. estimated_probabilities, confidence_level -> mispricing_analyst
    6. pricing_comparison, edge_analysis -> persona_recommender
    7. persona_recommendations -> scenario_analyst
    8. scenarios -> final_suggester
    9. final_output
    """

    # Initial input (required)
    user_market_input: str = ""

    # Market identification (from ingestor)
    market_title: Optional[str] = None
    market_url_or_id: Optional[str] = None
    input_validation_error: Optional[str] = None

    # Market mechanics (from parser)
    resolution_criteria: Optional[str] = None
    expiration_date: Optional[str] = None
    market_odds: list[MarketOdds] = field(default_factory=list)

    # Research (from researcher)
    research_summary: Optional[str] = None
    sources: list[str] = field(default_factory=list)

    # Probability estimates (from estimator)
    estimated_probabilities: list[ProbabilityEstimate] = field(default_factory=list)
    confidence_level: Optional[str] = None  # "low", "medium", "high"

    # Mispricing analysis (from analyst)
    pricing_comparison: list[PricingComparison] = field(default_factory=list)
    edge_analysis: Optional[str] = None

    # Persona recommendations (from recommender)
    persona_recommendations: list[PersonaRecommendation] = field(default_factory=list)

    # Scenarios (from scenario analyst)
    scenarios: list[Scenario] = field(default_factory=list)

    # Final output (from suggester)
    final_output: Optional[str] = None

    # Workflow metadata
    current_step: str = "not_started"
    errors: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        """Convert state to dictionary for serialization."""
        return {
            "user_market_input": self.user_market_input,
            "market_title": self.market_title,
            "market_url_or_id": self.market_url_or_id,
            "input_validation_error": self.input_validation_error,
            "resolution_criteria": self.resolution_criteria,
            "expiration_date": self.expiration_date,
            "market_odds": self.market_odds,
            "research_summary": self.research_summary,
            "sources": self.sources,
            "estimated_probabilities": self.estimated_probabilities,
            "confidence_level": self.confidence_level,
            "pricing_comparison": self.pricing_comparison,
            "edge_analysis": self.edge_analysis,
            "persona_recommendations": self.persona_recommendations,
            "scenarios": self.scenarios,
            "final_output": self.final_output,
            "current_step": self.current_step,
            "errors": self.errors,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "KalshiResearchState":
        """Create state from dictionary."""
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})
