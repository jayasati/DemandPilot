# Project

## Summary

DemandPilot answers three questions a retail planner asks every day, on real
data (M5/Walmart: 3,049 items × 10 stores × ~5.3 years of daily sales):

1. **How much will we sell?** — probabilistic daily demand forecasts
   (P10/P50/P90) per store/SKU.
2. **How much should we stock?** — newsvendor order quantities derived from
   the forecast quantile at the cost-implied critical fractile.
3. **What would policy X have cost us?** — historical simulation comparing
   inventory policies on realized demand.

## Goals

- Production-grade engineering: typed, tested, configuration-driven, documented.
- Statistically honest forecasting: leakage-safe features, direct multi-horizon
  quantiles, evaluation with pinball loss and coverage — never just RMSE.
- Decisions, not predictions: every forecast flows into an order quantity with
  an explicit cost rationale.
- Full transparency: every model run tracked in MLflow; every dataset snapshot
  versioned; every architectural choice recorded in an ADR.

## Non-goals

- Multi-echelon / network inventory optimization (single-location newsvendor
  only; see docs/KNOWN_LIMITATIONS.md).
- Real-time serving or streaming ingestion — this is a batch analytics platform.
- A multi-tenant SaaS product; deployment target is a single analyst machine or
  container.

## Stakeholders

- **Demand planners / inventory analysts** — dashboard and recommendations.
- **Executives** — generated summary reports with P&L impact.
- **Data scientists / engineers** — the pipeline, experiment tracking, and this
  repository as a reference implementation.
