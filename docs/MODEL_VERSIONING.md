# Model Versioning Strategy

## Mechanism

MLflow Model Registry (local file store by default; server via docker compose).
Configured in `configs/forecast.yaml` (`register_model`, `model_name`).

## What every registered model version records

- **Lineage**: feature snapshot id (docs/DATA_VERSIONING.md), git commit,
  full resolved config (logged as artifacts/params).
- **Quantile identity**: one LightGBM model per quantile — the quantile (and
  whether it is the cost-implied critical fractile) is a first-class tag, so
  P10/P50/P90 models are never confused.
- **Evaluation**: backtest metrics (pinball per quantile, coverage, WAPE,
  bias, RMSE) from the rolling-origin backtest, logged in the same run.

## Promotion policy (from Volume 3)

- `None` → `Staging`: automated — training run completed, metrics logged,
  invariants pass (quantile monotonicity P10 ≤ P50 ≤ P90, coverage within
  tolerance).
- `Staging` → `Production`: manual — requires a backtest comparison against the
  current production version; the comparison lands in the PR.
- Downstream consumers (optimization, simulation, dashboard) load only
  `Production` models by name — never a run id.

## Invariant

A model version with no recorded snapshot id or git commit is invalid by
definition and must not be promoted.
