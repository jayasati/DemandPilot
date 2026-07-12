"""Newsvendor order-quantity recommendations (ADR-003, ADR-012, ADR-016).

Translates the quantile forecasts from ``demandpilot.forecasting`` into
stocking decisions with explicit cost rationale. See ADR-016 for why
recommendations are computed retrospectively (at the most recent origin date
with a known outcome) rather than into genuinely unobserved future dates.
"""

from demandpilot.optimization.recommender import (
    RECOMMENDATIONS_TABLE,
    Recommendation,
    RecommendationBuilder,
    RecommendationReport,
    persist_recommendations,
)

__all__ = [
    "RECOMMENDATIONS_TABLE",
    "Recommendation",
    "RecommendationBuilder",
    "RecommendationReport",
    "persist_recommendations",
]
