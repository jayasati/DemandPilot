# 003. Use the newsvendor model for inventory optimization

## Status

Accepted; implemented in Volume 4 (single-point recommendations) and Volume 5
(historical replay quantifying the cost of the single-period simplification).

## Context

The stocking decision per store/SKU/period is: order quantity `Q` under
uncertain demand, where overstock costs `Co` per unit (unrecovered cost +
holding) and understock costs `Cu` per unit (lost margin + goodwill). This is
the classic single-period newsvendor problem with the closed-form optimum
`Q* = F⁻¹(Cu / (Cu + Co))` — the demand quantile at the critical fractile.
Alternatives (multi-period (s,S) policies, stochastic programming) need
lead-time demand processes and state that M5 doesn't provide, and would bury
the forecast→decision link the platform exists to demonstrate.

## Decision

The newsvendor model translates probabilistic forecasts into order quantities.
`Q*` is read directly from the critical-fractile quantile model's prediction
— no further numerical optimization is needed once that quantile is
forecast (`demandpilot.optimization.RecommendationBuilder`, reusing Volume 3's
`QuantileForecaster`). `core.newsvendor.critical_fractile` (Volume 0) computes
the fractile; `core.newsvendor.safety_stock` (Volume 4) reports the order
quantity's distance from the median forecast for context. See ADR-016 for the
retrospective-recommendation scope decision.

## Consequences

- Closed-form, explainable, and probabilistic by construction — it consumes
  the quantile forecasts natively; asymmetric costs are first-class.
- Single-period assumption: no inventory carryover or lead-time aggregation;
  (s,S)/multi-echelon are future extensions (docs/KNOWN_LIMITATIONS.md).
  Volume 5's historical replay (ADR-017) quantifies how much this
  simplification costs by comparing it against a classical baseline on real
  outcomes, without building a full multi-period simulator.
- Recommendations are computed retrospectively (ADR-016), not into
  genuinely unobserved future dates — a deliberate, documented scope
  boundary, not an oversight.
