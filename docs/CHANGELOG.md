# Changelog

All notable changes to this project are documented here.

Format based on [Keep a Changelog](https://keepachangelog.com/); this project
follows [Semantic Versioning](https://semver.org/).

## [Unreleased]

### Added — Volume 6 (reporting), 2026-07-12

- `demandpilot.mlflow_utils`: shared `resolve_mlflow_tracking_uri` (moved
  from `cli.py`) and new `latest_run(tracking_uri, experiment_name)` —
  read-only MLflow lookup via `MlflowClient(tracking_uri=...)`, verified
  against the installed MLflow version before writing code against it.
- `demandpilot.reporting.data`: gathers feature-snapshot lineage, the
  latest MLflow backtest run, and `recommendations`/`simulation_results`
  summaries — each optional, since a report can be built before any of
  `train`/`recommend`/`simulate` has ever run (checked via
  `information_schema.tables`, not assumed).
- `demandpilot.reporting.ReportBuilder`: renders a self-contained,
  dark-mode-aware executive HTML report (stat tiles + detail tables +
  cost-assumptions section), using the project's data-viz skill
  conventions (status-colored delta on the ML-savings tile, capped and
  labeled "largest misses" detail, no charts — this is a static summary).
- Report SQL: `sql/report_recommendations_summary.sql`,
  `sql/report_recommendations_top_misses.sql` (top 20 by absolute forecast
  error, count stated separately — never a silent cap),
  `sql/report_simulation_summary.sql`. Templates ship as package data under
  `demandpilot/reporting/templates/`, per the `.gitignore` note from
  Volume 0 that templates are code, not generated output.
- CLI: `demandpilot report [--snapshot-version N] [--output PATH]`.
- New exception `ReportingError`.
- New ADR: 018 (executive report design — templates-as-package-data,
  graceful-empty sections, read-only MLflow access).

### Added — Volume 5 (simulation), 2026-07-12

- `demandpilot.core.demand_distribution`: pure quantile estimators
  (`normal_quantile`, `poisson_quantile`, `empirical_bootstrap_quantile` —
  Monte Carlo bootstrap of lead-time demand from single-day observations)
  for the classical baseline policy.
- `demandpilot.core.newsvendor.realized_cost_breakdown` /
  `realized_cost`: the newsvendor cost function in real currency
  (cost ratios × sell price), split into understock/overstock components.
- `demandpilot.simulation.classical_order_up_to`: dispatches to the
  distribution estimators based on `configs/simulation.yaml`'s
  `demand_distribution`.
- `demandpilot.simulation.SimulationEngine`: replays the ML quantile policy
  against the classical baseline across many held-out historical decision
  points (reusing Volume 3's chronological split and Volume 3/4's assembler
  and forecaster), filtered to a `review_period_days` cadence, graded with
  the same newsvendor cost function — ADR-017.
- `demandpilot.simulation.persist_simulation_results`: materializes a
  `simulation_results` table (schema inferred, replaced wholesale, like
  `recommendations`).
- CLI: `demandpilot simulate [--snapshot-version N]`.
- New exception `SimulationError`.
- New ADR: 017 (policy-replay simulation design).

### Fixed

- `SimulationConfig.lead_time_days` tightened from `>= 0` to `>= 1`: `0`
  would self-join a row to itself in the horizon-based assembler (used by
  both `RecommendationBuilder` and `SimulationEngine`), predicting a row
  from its own future value — a latent leakage bug caught while designing
  Volume 5, never previously exercised.

### Added — Volume 4 (optimization), 2026-07-12

- `demandpilot.core.newsvendor.safety_stock`: order quantity's distance from
  the median forecast (positive or negative — both are valid outcomes of the
  newsvendor economics).
- `demandpilot.optimization.RecommendationBuilder`: reuses Volume 3's
  `HorizonDatasetAssembler`/`QuantileForecaster` to produce order-quantity
  recommendations — the critical-fractile quantile forecast itself is `Q*`,
  needing no further numerical optimization. Computed retrospectively at the
  most recent origin date with a known outcome (ADR-016), so every
  recommendation also carries the realized `actual_demand`.
- `demandpilot.optimization.persist_recommendations`: materializes a report
  into a `recommendations` table (schema inferred from the report, always
  replaced wholesale — a live operational output, not a versioned artifact
  like feature snapshots).
- CLI: `demandpilot recommend [--snapshot-version N] [--lead-time-days N]`
  (defaults to `configs/simulation.yaml`'s `lead_time_days`).
- New exception `OptimizationError`.
- Refactor: `latest_snapshot_table` moved from a private helper in
  `forecasting.pipeline` to a shared, public function in
  `features.snapshots` — both the forecasting and optimization layers resolve
  "the current snapshot" the same way.
- New ADR: 016 (recommendations computed retrospectively, not into
  unobserved future dates — a deliberate scope boundary explained in full).

### Added — Volume 3 (forecasting), 2026-07-12

- `demandpilot.forecasting.HorizonDatasetAssembler` / `assemble_multi_horizon`:
  self-join dataset assembly per ADR-008/014 — history-derived columns
  (lags/rolling stats) from the ORIGIN row, calendar/price/dimension columns
  from the TARGET row, stacked across horizons 1..`horizon_days` with
  `horizon` as a feature and configurable origin-date sampling (ADR-015).
- `demandpilot.forecasting.chronological_split`: time-ordered
  train/validation/test partitioning by origin date — never shuffled.
- `demandpilot.forecasting.QuantileForecaster`: one LightGBM quantile model
  per quantile (config quantiles ∪ the cost-implied critical fractile,
  ADR-012), with `demandpilot.core.metrics.enforce_monotonic_quantiles`
  correcting quantile crossing post-hoc.
- `demandpilot.core.metrics`: pinball loss, coverage, WAPE, bias, RMSE — pure
  functions, unit-tested against hand-computed values.
- `demandpilot.forecasting.ForecastingPipeline`: orchestrates assemble → split
  → train → backtest → MLflow logging (params, metrics, and optional model
  registration under `{model_name}-q{quantile}`).
- CLI: `demandpilot train [--snapshot-version N]`.
- `configs/forecast.yaml`: added `train.origin_stride_days`.
- Shared `demandpilot.features.naming` module (column-naming helpers factored
  out of the Volume 2 generator so the forecasting dataset assembler agrees
  on column names without duplicating the convention).
- New exception `ForecastError`.
- **MLflow tracking backend corrected to SQLite** (`sqlite:///mlruns/mlflow.db`):
  empirically verified that the installed MLflow (3.14) puts the plain
  filesystem tracking store into maintenance mode and raises on
  `start_run()`; ADR-006 updated accordingly. `demandpilot.cli.
  _resolve_mlflow_tracking_uri` resolves a relative `sqlite:///`/`file:` URI
  against `--root` (MLflow itself only resolves against cwd).
- New ADRs: 014 (future-known vs. history-derived feature split), 015
  (horizon-as-feature training + origin sampling).

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
