# 006. Use MLflow for experiment tracking

## Status

Accepted; implemented in Volume 3. Backend corrected from the original file
store to SQLite after empirical testing against the installed MLflow version
(see Decision).

## Context

Volume 3 trains many model variants (per quantile, per backtest fold, per
feature-set iteration). Without tracking, metric claims become unreproducible —
violating the project's "no fake metrics" rule, which requires every reported
number to trace to a run. Needs: params/metrics/artifacts logging, a model
registry with promotion stages, local-first operation. Alternatives: W&B
(hosted, account-bound), hand-rolled logging (reinvents the registry poorly).

## Decision

MLflow, with Model Registry for versioning/promotion; policies in
docs/EXPERIMENT_TRACKING.md and docs/MODEL_VERSIONING.md.

Tracking backend: **local SQLite** (`sqlite:///mlruns/mlflow.db`), not the
plain filesystem store originally planned. Verified empirically: MLflow 3.x
puts the file-based tracking backend into "maintenance mode" and raises
`MlflowException` on `mlflow.start_run()` unless
`MLFLOW_ALLOW_FILE_STORE=true` is set. SQLite is the equally zero-ops,
no-server-required local equivalent and isn't deprecated, so it's the correct
default rather than working around the deprecation warning. The CLI resolves
a relative `sqlite:///` (or `file:`) URI against `--root`, since MLflow itself
only resolves relative URIs against the process's current working directory
(`demandpilot.cli._resolve_mlflow_tracking_uri`).

## Consequences

- Every training run records config, git commit, snapshot id, and metrics —
  reports can cite runs instead of hand-typed numbers.
- SQLite is single-writer like DuckDB (ADR-001) — consistent with the
  project's existing single-machine, single-pipeline-writer posture; a real
  multi-user deployment would need a server-backed store (Postgres + an
  `mlflow server` process) — accepted, not needed at this scale.
- MLflow is a heavy dependency; it stays quarantined in
  `demandpilot.forecasting.pipeline` so nothing else imports it.
- This is a concrete instance of why ADRs get corrected rather than trusted
  blindly (CLAUDE.md's "challenge your own decisions"): the original plan was
  reasonable when written and wrong once tested against the real dependency
  version.
