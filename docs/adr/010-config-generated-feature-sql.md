# 010. Generate feature SQL from features.yaml

## Status

Accepted; implemented in Volume 2.

## Context

The feature set was defined twice: lags/windows in `configs/features.yaml` AND
hand-written in `sql/rolling_features.sql`, with "keep in sync" comments — a
DRY violation that guarantees eventual drift, and the drift would be silent
(a window added in YAML but not SQL just never exists). Alternatives:
compute features in Polars from config (loses DuckDB's out-of-core window
performance over 59M rows); treat SQL as the source of truth (config can no
longer drive experiments).

## Decision

`configs/features.yaml` is the single source of truth.
`demandpilot.features.generator.FeatureSqlGenerator` builds the
`rolling_features` view's `SELECT` list in Python from the validated
`FeaturesConfig` (one `LAG(...)` expression per configured lag, one windowed
aggregation per window × aggregation pair) and renders it into the Jinja2
template `sql/rolling_features.sql.j2` (ADR-005). Every window's upper bound
(`1 PRECEDING`) is hardcoded in the template, not derived from config — so the
leakage rule (ADR-008) holds structurally even if a future config allowed it.

`sql/feature_store.sql` (the dimensional join) stays a static, hand-written
view, but selects `rf.* EXCLUDE (store_id, sku_id, date)` instead of naming
every rolling-feature column — so it never needs updating when the lag/window
set in config changes; only the generator does.

## Consequences

- One place to change the feature set: edit `configs/features.yaml`, run
  `demandpilot build-features`. No SQL file to hand-edit or forget.
- DuckDB binds views eagerly (verified empirically), so `rolling_features` and
  `feature_store` must be created together and are excluded from the static
  schema (`sql/create_tables.sql`/`views.sql`) — they're built by
  `FeatureSnapshotBuilder` instead (ADR-011).
- Verified by `tests/unit/test_feature_generator.py` (one expression per
  config entry, never `CURRENT ROW`) and end-to-end by
  `tests/integration/test_features.py`.
