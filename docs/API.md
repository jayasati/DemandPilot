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
- `demandpilot.core.newsvendor.critical_fractile(cu, co) -> float`.
- `demandpilot.sqlrender.SqlRenderer(sql_dir).render(name, **params) -> str`.

Anything prefixed with `_` is private and may change without notice. Errors are
always subclasses of `demandpilot.exceptions.DemandPilotError`.
