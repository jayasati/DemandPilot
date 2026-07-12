# Data Versioning Strategy

Full rationale in [ADR-011](adr/011-snapshot-data-versioning.md); summary here.

## What is versioned, and how

| Artifact | Mechanism |
|---|---|
| Raw M5 CSVs | **Immutable upstream** — Kaggle competition data never changes; `scripts/download_m5.py` re-fetches byte-identical files. Not committed, not copied. |
| DuckDB base tables | Deterministic function of (raw data, ingestion SQL, config) — all three are in git, so the tables are reproducible with `demandpilot ingest-m5`. |
| **Training feature snapshots** | Materialized as `feature_store_v{N}` tables (Volume 2) with a manifest recording: snapshot id, creation date, git commit of the generating code, config hash, row count, date range. Models train only on snapshots, never on live views. |

## Why not DVC / lakeFS?

Single machine, single immutable upstream dataset, DuckDB-native workflow —
external data-versioning infrastructure would add operational surface without
adding reproducibility (YAGNI). The decision is revisited if the project ever
ingests mutable or multiple upstream sources.

## Invariants

- Anything under `data/` is disposable and reconstructible from git + Kaggle.
- A model in MLflow always references the snapshot id it trained on
  (docs/MODEL_VERSIONING.md), closing the loop: model → snapshot → git commit
  → raw data.
