# Experiment Tracking Strategy

## Tool & layout

MLflow (ADR-006). Local file store `file:./mlruns` for development; the compose
stack runs a tracking server on :5000 for a browsable UI. Experiments:

- `demandpilot-forecast` — model training and backtests (one run per training,
  nested runs per quantile).
- Simulation experiments get their own experiment name in Volume 5 so policy
  comparisons don't mix with model training.

## What every run logs

- **Params**: resolved forecast + feature config (flattened), quantile, horizon,
  snapshot id, git commit.
- **Metrics**: pinball (per quantile), coverage, WAPE, bias, RMSE — per
  backtest fold and aggregated.
- **Artifacts**: feature importance, backtest plots, the exact rendered
  feature SQL.

## Rules

- No untracked training: the training entry point *is* the MLflow run — there
  is no code path that fits a model outside a run context.
- Runs are cheap; deleting is allowed only for crashed runs. Failed experiments
  stay — negative results are information.
- Metrics reported anywhere (docs, reports, dashboard) must be reproducible
  from a referenced MLflow run. **No hand-typed metrics.**
