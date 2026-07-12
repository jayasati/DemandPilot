# 002. Use LightGBM for demand forecasting

## Status

Accepted

## Context

Forecasting 30,490 series (store × SKU) of daily units with rich tabular
covariates (price, SNAP, events, calendar, hierarchy). Requirements: one
*global* model over all series (per-series classical models like ARIMA/ETS
can't share strength across 30k mostly-sparse series and are operationally
heavy), native quantile objectives for probabilistic output, categorical
handling, and CPU-feasible training. Deep learning forecasters (DeepAR, TFT)
add GPU/tuning cost that isn't justified before a gradient-boosting baseline —
which won the actual M5 competition.

## Decision

LightGBM is the forecasting model: one global model per quantile, trained on
the feature store with the `quantile` objective (see ADR-008 for the horizon
strategy, ADR-012 for the quantile set).

## Consequences

- Fast CPU training, strong tabular accuracy, native categoricals and
  monotonic constraints if needed; well-supported by MLflow.
- Long-horizon sequence patterns are captured only through engineered
  lags/rollings — feature quality is the model (hence ADR-010's investment).
- Independently trained quantile models can cross (P10 > P50); monitored and
  post-sorted if observed (docs/KNOWN_LIMITATIONS.md).
