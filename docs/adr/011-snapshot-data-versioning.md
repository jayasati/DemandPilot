# 011. Versioned feature snapshots as the data versioning strategy

## Status

Accepted (implementation lands in Volume 2)

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

Training data is materialized: `CREATE TABLE feature_store_v{N} AS SELECT ...`
in DuckDB, with a manifest table recording snapshot id, timestamp, git commit
of the generating code, config hash, row count, and date range. Models train
only on snapshots; MLflow runs record the snapshot id (docs/MODEL_VERSIONING.md).
Everything under `data/` remains disposable and reconstructible.

## Consequences

- Full lineage chain: model → snapshot → git commit + config → immutable raw
  data. Backtests are re-runnable on the exact bytes a model saw.
- Snapshots cost disk (~GBs each at M5 scale) — acceptable locally; a pruning
  policy (keep last K + any referenced by a registered model) comes with
  Volume 3.
- Revisit if the project ever ingests mutable upstream data — that's the point
  where DVC-style tooling earns its keep.
