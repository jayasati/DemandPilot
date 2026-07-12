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
- **Direct**: for horizon h, every lag/rolling feature is shifted by at least
  h, so the model at horizon h only sees information available at forecast
  time. Statistically valid per-horizon quantiles at the cost of more feature
  engineering (and either per-horizon models or a horizon feature).

A related leakage rule falls out of the same principle: **no feature window may
include the current row's target** — the original hand-written rolling SQL
violated this (windows ended at `CURRENT ROW`) and was fixed in Volume 0.

## Decision

Direct multi-horizon forecasting. `configs/forecast.yaml` accepts only
`strategy: direct`. The Volume 2 feature generator shifts all
target-derived features by the forecast horizon; the leakage rule is enforced
structurally (windows end at ≥1 PRECEDING; lags ≥ horizon at inference
features) and by an automated leakage test suite in CI.

## Consequences

- Honest probabilistic forecasts at every horizon; backtest metrics
  (pinball, coverage) mean what they claim.
- More feature plumbing: features are horizon-parameterized, which ADR-010's
  config-driven SQL generation absorbs.
- Training cost multiplies by the number of quantiles (and possibly horizons);
  accepted — LightGBM is fast and the M5 winner used the same family of
  approach.
