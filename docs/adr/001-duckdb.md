# 001. Use DuckDB for local/analytical data storage

## Status

Accepted

## Context

The platform needs fast analytical SQL (window functions, large joins,
unpivots) over ~59M rows of retail sales on a single developer machine, with
zero operational overhead and native CSV/Parquet reading for ingestion.
Alternatives: SQLite (row store — too slow for analytical scans and window
functions at this scale), Postgres (a server to install/manage for no gain on
one machine), pure dataframes (no persistent queryable store, SQL logic would
migrate into Python code).

## Decision

DuckDB is the primary analytical store and query engine. One database file
(`data/demandpilot.duckdb`, path in `configs/app.yaml`). Pipelines are the sole
writer; every other consumer connects read-only (`Database.connect(read_only=True)`).

## Consequences

- Columnar, vectorized execution makes ingest/feature SQL fast with no tuning;
  direct `read_csv` ingestion; excellent Polars interop (zero-copy Arrow).
- Single-node and effectively single-writer: concurrent pipeline runs against
  the same file are forbidden — an accepted constraint (docs/KNOWN_LIMITATIONS.md).
- Scale ceiling: fine to ~10× M5; beyond that, revisit (MotherDuck/warehouse —
  SQL is largely portable).
