# Model Versioning Strategy

## Mechanism

MLflow Model Registry, local SQLite backend by default (ADR-006). Registration
is controlled by `configs/forecast.yaml`'s `mlflow.register_model` /
`mlflow.model_name`. **One registered model per quantile**, named
`{model_name}-q{quantile}` (e.g. `demandpilot-forecast-model-q0_1`) — so
P10/P50/P90 are distinct, independently versioned registry entries, never
confused with each other.

## What every registered model version records (as of Volume 3)

- The trained LightGBM booster itself (`mlflow.lightgbm.log_model`).
- **Lineage, via the run it belongs to**: the exact `feature_store_v{N}`
  snapshot table trained on (a run param — traceable to that snapshot's git
  commit and config hash in the `feature_snapshots` manifest, ADR-011),
  `horizon_days`, `origin_stride_days`, and every LightGBM hyperparameter.
- **Evaluation, via the same run**: pinball loss and coverage for every
  quantile, plus WAPE/bias/RMSE from the median model.

## Not yet implemented

Automatic stage promotion (`None` → `Staging` → `Production`) is **not**
built — every call to `demandpilot train` with `register_model: true` creates
a new model version with no stage assigned. A promotion policy (backtest
comparison against the current production version, invariant checks such as
quantile monotonicity before promoting) is planned once there is a second
volume's worth of models to actually compare against; documenting an
unbuilt promotion workflow here would violate the "never generate fake
implementations" rule. Downstream consumers (optimization, simulation,
dashboard, from Volume 4 onward) should load a specific version explicitly
until promotion exists.

## Invariant

A model version whose run has no `snapshot_table` param is invalid by
definition and must not be relied upon — `ForecastingPipeline` always logs
this param, so its absence indicates a run that bypassed the pipeline.
