# 006. Use MLflow for experiment tracking

## Status

Accepted

## Context

Volume 3 trains many model variants (per quantile, per backtest fold, per
feature-set iteration). Without tracking, metric claims become unreproducible —
violating the project's "no fake metrics" rule, which requires every reported
number to trace to a run. Needs: params/metrics/artifacts logging, a model
registry with promotion stages, local-first operation. Alternatives: W&B
(hosted, account-bound), hand-rolled logging (reinvents the registry poorly).

## Decision

MLflow with a local file store (`file:./mlruns`) by default and a compose
service for the UI; Model Registry for versioning/promotion. Policies in
docs/EXPERIMENT_TRACKING.md and docs/MODEL_VERSIONING.md.

## Consequences

- Every training run records config, git commit, snapshot id, and metrics —
  reports can cite runs instead of hand-typed numbers.
- The file store is single-user and unauthenticated — fine locally; a real
  deployment would need a backing server/DB (accepted).
- MLflow is a heavy dependency; it stays quarantined in the forecasting
  layer's tracking module so nothing else imports it.
