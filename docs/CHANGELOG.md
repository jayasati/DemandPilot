# Changelog

All notable changes to this project are documented here.

Format based on [Keep a Changelog](https://keepachangelog.com/); this project
follows [Semantic Versioning](https://semver.org/).

## [Unreleased]

### Added — Volume 2 (feature engineering), 2026-07-12

- `demandpilot.features.FeatureSqlGenerator`: renders the `rolling_features`
  view SQL from `configs/features.yaml` — one `LAG(...)` per configured lag,
  one windowed aggregation per window × aggregation pair, every window
  hardcoded to end at `1 PRECEDING` regardless of config (ADR-010).
- `demandpilot.features.FeatureSnapshotBuilder`: builds `rolling_features` +
  `feature_store`, then materializes a versioned `feature_store_v{N}` table
  with a `feature_snapshots` lineage manifest (version, git commit, config
  hash, row count, date range — ADR-011).
- CLI: `demandpilot build-features`.
- `sql/feature_store.sql` now selects `rf.* EXCLUDE (store_id, sku_id, date)`
  instead of naming every rolling-feature column — stays valid across config
  changes with no edits.
- Leakage test suite (`tests/integration/test_features.py`,
  `tests/unit/test_feature_generator.py`): generated SQL never contains
  `CURRENT ROW`, materialized snapshots reproduce the leakage-safety property
  end-to-end.
- New exception `FeatureError`.
- ADR-008 corrected: direct multi-horizon forecasting uses the target-shift
  formulation (one leakage-safe feature snapshot serves every horizon; Volume
  3 pairs it with a horizon-shifted target) rather than per-horizon feature
  shifting — simpler and equivalent.

### Added — Volume 0 (foundation) & Volume 1 (data layer), 2026-07-12

- Typed configuration system: all `configs/*.yaml` validated into frozen
  Pydantic models via a single `load_config()` entry point (ADR-009).
- Structured exception hierarchy rooted at `DemandPilotError`.
- Logging bootstrap with rotating JSON file output under `logs/`.
- Newsvendor critical-fractile domain math (`demandpilot.core.newsvendor`).
- DuckDB star schema for M5 (stores, skus, calendar, prices, sales) with
  reporting views; leakage-safe rolling-feature view (ADR-008).
- M5 ingestion pipeline: staged CSV load, wide→long unpivot, weekly price
  join, pre-launch row filtering, idempotent re-runs (ADR-013).
- 13-check data validation suite that runs after every ingest.
- CLI: `demandpilot init-db | ingest-m5 | validate`.
- Kaggle download script (`scripts/download_m5.py`).
- Test suite: 38 unit + integration tests on deterministic M5-format
  fixtures; 94% branch coverage (85% gate).
- Tooling: Poetry, Black, Ruff (incl. docstring enforcement), MyPy strict,
  pre-commit, poethepoet tasks, GitHub Actions CI (3.12/3.13).
- Docker: multi-stage image + compose with an MLflow tracking service.
- Documentation set: architecture, system flow, data model, strategies
  (testing, logging, exceptions, git, docker, data/model versioning,
  experiment tracking), workflow, Definition of Done, contribution guide,
  review checklist, risk register, known limitations, 13 ADRs.

### Changed

- Forecast configuration is probabilistic-first: quantile objective,
  P10/P50/P90, pinball/coverage metrics, direct multi-horizon strategy
  (was: regression/RMSE).
- Rolling-feature SQL excludes the current row from all windows (target
  leakage fix).
- Costs reworked to sell-price ratios with validated, documented assumptions.

### Removed

- `sql/calendar.sql` (generated range calendar) — the calendar is now
  ingested from M5's `calendar.csv`, including real events.
