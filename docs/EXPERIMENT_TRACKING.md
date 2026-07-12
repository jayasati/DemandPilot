# Experiment Tracking Strategy

## Tool & layout

MLflow (ADR-006). Local SQLite backend `sqlite:///mlruns/mlflow.db` by
default (the plain file store is deprecated in MLflow >=3 — see ADR-006); the
compose stack runs a tracking server on :5000 for a browsable UI, also backed
by SQLite. Experiment: `demandpilot-forecast` (`forecast.yaml`'s
`mlflow.experiment_name`) — one run per `demandpilot train` invocation,
covering every quantile trained in that run.
Simulation experiments will get their own experiment name in Volume 5 so
policy comparisons don't mix with model training.

## What every run logs (`demandpilot.forecasting.pipeline.ForecastingPipeline`)

- **Params**: `snapshot_table` (the exact `feature_store_v{N}` trained on —
  ADR-011 lineage), `horizon_days`, `origin_stride_days`, `quantiles`, and
  every LightGBM hyperparameter (`model__*`).
- **Metrics**: `pinball_q{...}` and `coverage_q{...}` per quantile;
  `wape`/`bias`/`rmse` from the median (P50) model; row counts for each split.
- **Models**: when `forecast.yaml`'s `mlflow.register_model` is true, each
  quantile's booster is logged and registered under
  `{model_name}-q{quantile}` (`mlflow.lightgbm.log_model`).

Git commit lineage is currently only on the *snapshot* (via `feature_snapshots.
git_commit`, ADR-011), not yet duplicated as a run tag — the snapshot table
name in the run params is enough to look it up. Revisit if runs need to be
queryable by commit directly.

## Rules

- No untracked training: `demandpilot train` / `ForecastingPipeline.run()` *is*
  the MLflow run — there is no code path that fits a model outside a run
  context.
- Runs are cheap; deleting is allowed only for crashed runs. Failed experiments
  stay — negative results are information.
- Metrics reported anywhere (docs, reports, dashboard) must be reproducible
  from a referenced MLflow run. **No hand-typed metrics.**
