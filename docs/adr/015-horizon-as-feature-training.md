# 015. Horizon-as-feature training with origin sampling

## Status

Accepted; implemented in Volume 3.

## Context

`forecast.yaml` requires forecasts for horizons 1..28 days ahead. Training a
separate LightGBM model per horizon (28 models × N quantiles) multiplies
training cost linearly and complicates deployment (which of 28 models serves
a given day?) for a benefit that's marginal once genuine future-known
covariates are used per horizon (ADR-014) — the horizon itself is just
another number the model can condition on.

Separately, stacking every origin date × every horizon for M5's ~30,490
series would produce an enormous assembled dataset (tens to hundreds of
millions of rows) that doesn't fit comfortably in memory on a single
development machine, and most of those rows are highly redundant (adjacent
days rarely differ enough to be independently informative for training).

## Decision

1. **One model per quantile, not per (quantile, horizon)**: the assembled
   dataset stacks horizons `1..horizon_days` for each origin, with `horizon`
   included as a plain numeric feature (`demandpilot.forecasting.dataset.
   assemble_multi_horizon`). One `QuantileForecaster` per quantile level then
   generalizes across every horizon.
2. **Origin sampling**: `forecast.yaml`'s `train.origin_stride_days` (default
   `7`) subsamples origins to 1-in-N calendar days, filtered on
   `(date - epoch) % stride = 0` so every horizon draws from the *same*
   calendar dates (not an independently-random subset per horizon, which
   would break the ability to compare across horizons). `1` disables
   subsampling entirely.

## Consequences

- Training cost is `O(quantiles)` instead of `O(quantiles × horizons)`.
- A single model per quantile may fit horizon-dependent effects slightly less
  precisely than 28 specialized models — an accepted accuracy/cost trade-off,
  revisit if backtests show horizon-dependent error patterns the shared model
  can't capture (docs/KNOWN_LIMITATIONS.md).
- Origin sampling is a documented, logged reduction
  (`ForecastingPipeline` logs the assembled row count), not a silent cap —
  satisfies the project's "no silent truncation" principle.
- At the default M5 scale this still produces a large dataset; `origin_stride_days`
  is the primary lever for keeping a training run tractable on a laptop
  (risk R3) — tune upward for a first real run, downward once memory/runtime
  budgets are known.
