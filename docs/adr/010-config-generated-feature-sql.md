# 010. Generate feature SQL from features.yaml

## Status

Accepted (implementation lands in Volume 2)

## Context

The feature set was defined twice: lags/windows in `configs/features.yaml` AND
hand-written in `sql/rolling_features.sql`, with "keep in sync" comments — a
DRY violation that guarantees eventual drift, and the drift would be silent
(a window added in YAML but not SQL just never exists). Alternatives:
compute features in Polars from config (loses DuckDB's out-of-core window
performance over 59M rows); treat SQL as the source of truth (config can no
longer drive experiments or per-horizon shifts).

## Decision

`configs/features.yaml` is the single source of truth. Volume 2 adds a feature
SQL generator: Jinja2 templates (ADR-005) render lag/rolling expressions from
the validated `FeaturesConfig`, parameterized by forecast horizon (ADR-008),
executed in DuckDB, and materialized as versioned snapshots (ADR-011). The
rendered SQL is logged as an MLflow artifact for auditability. Until the
generator lands, `sql/rolling_features.sql` is a hand-mirrored reference
implementation (flagged in docs/KNOWN_LIMITATIONS.md).

## Consequences

- One place to change the feature set; per-horizon variants come free from a
  template parameter; leakage rules are enforced in one generator instead of
  N hand-written files.
- Generated SQL is one step removed from what's in git — mitigated by logging
  the rendered SQL and by golden-file tests on the generator output.
