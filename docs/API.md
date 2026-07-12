# API Surface

DemandPilot currently exposes two surfaces: a CLI and the `demandpilot` Python
package. (No HTTP API — see PROJECT.md non-goals; a FastAPI layer is a listed
future extension.)

## CLI (`demandpilot`)

Global options: `--root PATH` (project root; default `DEMANDPILOT_ROOT` env var
or the current directory), `--version`.

| Command | Effect | Exit code |
|---|---|---|
| `init-db` | Create all tables and views from `sql/` | 0 / 1 on error |
| `ingest-m5 [--raw-dir PATH]` | Ingest the M5 CSVs, then run the validation suite | 1 if ingest **or validation** fails |
| `build-features` | Generate `rolling_features`/`feature_store` from config and materialize a new `feature_store_v{N}` snapshot | 0 / 1 on error |
| `train [--snapshot-version N]` | Assemble a multi-horizon dataset from a feature snapshot (latest by default), chronologically split, train quantile models, backtest, log to MLflow | 0 / 1 on error |
| `recommend [--snapshot-version N] [--lead-time-days N]` | Build newsvendor order-quantity recommendations (retrospective — ADR-016) and persist them to the `recommendations` table | 0 / 1 on error |
| `simulate [--snapshot-version N]` | Replay the ML quantile policy vs. the classical baseline over historical decisions (ADR-017) and persist to the `simulation_results` table | 0 / 1 on error |
| `report [--snapshot-version N] [--output PATH]` | Render the executive HTML report (ADR-018); every section degrades gracefully if its upstream command hasn't run yet | 0 / 1 on error |
| `validate` | Re-run the 13-check validation suite | 1 on any failing check |

All commands read configuration exclusively from `<root>/configs/` and log to
console + `logs/demandpilot.log`.

## Python package entry points

Stable, typed, documented interfaces intended for reuse (e.g. notebooks):

- `demandpilot.config.load_config(root) -> DemandPilotConfig` — validated config aggregate.
- `demandpilot.data.Database(path)` — DuckDB handle; `connect(read_only=...)` context manager.
- `demandpilot.data.apply_schema(db, sql_dir)` — create tables/views.
- `demandpilot.data.M5Ingestor(db, renderer, raw_dir).ingest() -> IngestionSummary`.
- `demandpilot.data.DataValidator(db).run() -> ValidationReport`.
- `demandpilot.features.FeatureSqlGenerator(renderer).render(features_config) -> str`.
- `demandpilot.features.FeatureSnapshotBuilder(db, sql_dir, root).build(features_config) -> SnapshotInfo`.
- `demandpilot.forecasting.assemble_multi_horizon(connection, assembler, features_config, snapshot_table, horizon_days, origin_stride_days) -> pl.DataFrame`.
- `demandpilot.forecasting.chronological_split(dataset, train_config) -> DatasetSplit`.
- `demandpilot.forecasting.ForecastingPipeline(sql_dir).run(connection, features_config, forecast_config, costs_config, snapshot_table=None) -> BacktestReport`.
- `demandpilot.optimization.RecommendationBuilder(sql_dir).build(connection, features_config, forecast_config, costs_config, lead_time_days, snapshot_table=None) -> RecommendationReport`.
- `demandpilot.optimization.persist_recommendations(connection, report) -> None`.
- `demandpilot.simulation.SimulationEngine(sql_dir).run(connection, features_config, forecast_config, costs_config, simulation_config, snapshot_table=None) -> PolicyComparison`.
- `demandpilot.simulation.persist_simulation_results(connection, comparison) -> None`.
- `demandpilot.simulation.classical_order_up_to(daily_demand, lead_time_days, service_level, demand_distribution, n_simulations, random_seed) -> float`.
- `demandpilot.reporting.ReportBuilder(sql_dir).build(connection, forecast_config, costs_config, tracking_uri, output_path, snapshot_table=None) -> Path`.
- `demandpilot.reporting.gather_report_data(connection, sql_dir, forecast_config, costs_config, tracking_uri, snapshot_table) -> ReportData`.
- `demandpilot.mlflow_utils.resolve_mlflow_tracking_uri(tracking_uri, root) -> str`; `latest_run(tracking_uri, experiment_name) -> RunSummary | None`.
- `demandpilot.core.newsvendor.critical_fractile(cu, co) -> float`; `safety_stock(order_quantity, median_demand) -> float`; `realized_cost_breakdown(...) -> tuple[float, float]`.
- `demandpilot.core.demand_distribution`: `normal_quantile`, `poisson_quantile`, `empirical_bootstrap_quantile`.
- `demandpilot.core.metrics`: `pinball_loss`, `coverage`, `wape`, `bias`, `rmse`, `enforce_monotonic_quantiles`.
- `demandpilot.sqlrender.SqlRenderer(sql_dir).render(name, **params) -> str`.

Anything prefixed with `_` is private and may change without notice. Errors are
always subclasses of `demandpilot.exceptions.DemandPilotError`.
