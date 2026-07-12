# 011. Versioned feature snapshots as the data versioning strategy

## Status

Accepted; implemented in Volume 2.

## Context

Two problems, one mechanism. **Reproducibility**: `feature_store` is a view —
it reflects whatever is in `sales` right now, so a model trained "on the view"
is trained on unversioned data. **Performance**: the view recomputes window
functions over ~59M rows on every read. Heavyweight alternatives (DVC, lakeFS)
version file blobs, but our raw data is an immutable Kaggle competition
dataset and every derived table is a deterministic function of (raw data, git
commit, config) — external tooling would add ops surface without adding
reproducibility.

## Decision

`demandpilot.features.FeatureSnapshotBuilder.build()` materializes
`CREATE TABLE feature_store_v{N} AS SELECT * FROM feature_store`, where `N`
auto-increments from a `feature_snapshots` manifest table
(`sql/feature_snapshots.sql`) recording: `version`, `table_name`,
`created_at`, `git_commit` (via `git rev-parse HEAD`, `NULL` if unavailable —
e.g. no git installed), `config_hash` (SHA-256 of the resolved
`FeaturesConfig`, truncated), `row_count`, `min_date`, `max_date`. Models train
only on a named snapshot table, never on the live `feature_store` view.
Everything under `data/` remains disposable and reconstructible.

## Consequences

- Full lineage chain: model → snapshot → git commit + config → immutable raw
  data. Backtests are re-runnable on the exact bytes a model saw.
- Snapshots cost disk (~GBs each at M5 scale) — acceptable locally; a pruning
  policy (keep last K + any referenced by a registered model) comes with
  Volume 3, alongside wiring the snapshot id into MLflow runs
  (docs/MODEL_VERSIONING.md).
- Revisit if the project ever ingests mutable upstream data — that's the point
  where DVC-style tooling earns its keep.
- Verified end-to-end by `tests/integration/test_features.py` (version
  increments, manifest lineage matches the built table, row counts match
  `sales`, no current-day leakage in the materialized table).
