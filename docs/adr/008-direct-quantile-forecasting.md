# 008. Direct multi-horizon quantile forecasting (no recursion)

## Status

Accepted

## Context

The platform must produce P10/P50/P90 for horizons up to 28 days. With lag
features, a horizon-h prediction cannot use lags shorter than h at inference —
the values don't exist yet. Two standard resolutions:

- **Recursive**: predict one step, feed the prediction back as a lag, repeat.
  Simple, but errors compound — and, decisively, *quantiles do not compose
  recursively*: feeding a P90 prediction back as an input does not produce a
  valid 28-day-ahead P90. Recursive probabilistic forecasts require simulating
  full sample paths, which quantile GBMs don't provide.
- **Direct**: the model at horizon h only sees information available at
  forecast time. Statistically valid per-horizon quantiles.

A related leakage rule falls out of the same principle: **no feature window may
include the current row's target** — the original hand-written rolling SQL
violated this (windows ended at `CURRENT ROW`) and was fixed in Volume 0.

## Decision

Direct multi-horizon forecasting, via the **target-shift formulation**:
`rolling_features`/`feature_store` (ADR-010) are computed *as of* each date
`d`, using only history strictly before `d` (every window ends at
`1 PRECEDING`, every lag is `>= 1`) — this makes the feature row at `d`
simultaneously valid for **every** horizon `h >= 1`, since it never depends on
`h`. Volume 3's dataset assembly then pairs `features_asof(d)` with the label
`units_sold` at `d + h` for each configured horizon, training one quantile
model per horizon (or a horizon-as-feature variant). `configs/forecast.yaml`
accepts only `strategy: direct`.

This is simpler than literally shifting each feature by `h` (no per-horizon
feature tables, no duplicated generation work) and is exactly equivalent: a
feature known "as of yesterday" is valid input regardless of how many days
ahead the target is. The leakage rule is enforced structurally by the
generator (ADR-010) and by an automated leakage test suite
(`tests/integration/test_features.py`).

## Consequences

- Honest probabilistic forecasts at every horizon; backtest metrics
  (pinball, coverage) mean what they claim.
- **One** feature snapshot serves all horizons — no per-horizon feature
  generation or storage duplication; Volume 3 only needs a horizon-aware
  target join.
- Training cost multiplies by the number of quantiles × horizons (whether via
  separate models or a horizon feature) — accepted; LightGBM is fast and the
  M5 winner used the same family of approach.
