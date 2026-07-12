# 012. Couple forecast quantiles to newsvendor economics

## Status

Accepted (training-side implementation lands in Volume 3)

## Context

The newsvendor optimum is the demand quantile at the critical fractile
`Cu/(Cu+Co)` (ADR-003). A fixed P10/P50/P90 forecast cannot answer an
arbitrary fractile — if costs imply 0.58, interpolating between P50 and P90
injects an unmodeled distributional assumption exactly where money is decided.
Separately, M5 provides sell prices but no procurement costs, so absolute
per-unit costs can't be data-derived and per-SKU absolute values wouldn't
transfer across a 3,049-item catalog.

## Decision

1. **Costs are ratios of sell price** (`configs/costs.yaml`): unit cost,
   salvage, holding, and stockout-penalty ratios — documented assumptions,
   validated at load time (salvage < cost; a well-defined fractile is
   guaranteed or the config is rejected).
2. **The effective training quantile set is** `quantiles ∪ {critical fractile}`:
   the optimizer consumes a quantile the model was actually trained at, never
   an interpolation. `CostsConfig.critical_fractile` (computed via
   `core.newsvendor.critical_fractile`) is available since Volume 0.

## Consequences

- The forecast→decision hand-off is exact and auditable; changing costs
  visibly changes which quantile gets trained (and triggers retraining).
- One extra LightGBM model per training run — cheap.
- Cost ratios are assumptions, not data (risk R8): reports must label them,
  and Volume 4 includes fractile sensitivity analysis.
