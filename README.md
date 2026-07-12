# DemandPilot

Decision-intelligence platform for retail demand forecasting, inventory
optimization, and business simulation — built on the
[M5 (Walmart) dataset](https://www.kaggle.com/competitions/m5-forecasting-accuracy).

DemandPilot forecasts probabilistic demand (P10/P50/P90) per store/SKU with
quantile LightGBM, converts forecasts into order quantities with the newsvendor
model, replays historical inventory policies to quantify their P&L impact, and
delivers results through generated executive reports and a Streamlit dashboard.

## Status

| Volume | Scope | Status |
|---|---|---|
| 0 | Foundation: tooling, CI, docs, config system | ✅ done |
| 1 | Data layer: M5 ingestion, schema, validation | ✅ done |
| 2 | Feature engineering (config-generated SQL) | ⏳ next |
| 3–8 | Forecasting → optimization → simulation → reporting → dashboard → hardening | planned |

See [docs/ROADMAP.md](docs/ROADMAP.md).

## Quick start

Requirements: Python 3.12+ and [Poetry](https://python-poetry.org/). Full
instructions (including Windows notes and Kaggle credentials) are in
[docs/ENVIRONMENT_SETUP.md](docs/ENVIRONMENT_SETUP.md).

```bash
poetry install --with dev
poetry run poe check                     # format check, lint, typecheck, tests

# Get the data (needs Kaggle credentials + accepted competition rules)
poetry run python scripts/download_m5.py

# Build and validate the database
poetry run demandpilot init-db
poetry run demandpilot ingest-m5         # ingests, then runs the validation suite
poetry run demandpilot validate
```

The DuckDB database lands at `data/demandpilot.duckdb` (configurable in
`configs/app.yaml`; nothing is hardcoded).

## Repository layout

```
configs/     All runtime configuration (validated by Pydantic at load time)
data/        Raw + processed data and the DuckDB file (gitignored)
docs/        Architecture, strategies, ADRs, roadmap
sql/         All SQL: schema, views, and Jinja2 ingestion templates
src/         The demandpilot package (core / config / data / cli layers)
tests/       Unit + integration tests (deterministic M5-format fixtures)
scripts/     Operational scripts (dataset download)
docker/      Dockerfile + compose (app + MLflow)
.github/     CI workflow and PR template
```

## Documentation map

- [Architecture](docs/ARCHITECTURE.md) · [System flow](docs/SYSTEM_FLOW.md) · [Data model](docs/DATA_MODEL.md)
- [Tech stack](docs/TECH_STACK.md) · [ADRs](docs/adr/README.md) · [API/CLI](docs/API.md)
- [Development workflow](docs/DEVELOPMENT_WORKFLOW.md) · [Definition of Done](docs/DEFINITION_OF_DONE.md) · [Contributing](CONTRIBUTING.md)
- [Testing strategy](docs/TESTING.md) · [Coding standards](docs/CODING_STANDARDS.md) · [Code review checklist](docs/CODE_REVIEW_CHECKLIST.md)
- [Risk register](docs/RISK_REGISTER.md) · [Known limitations](docs/KNOWN_LIMITATIONS.md)

## License

MIT — see [LICENSE](LICENSE).
