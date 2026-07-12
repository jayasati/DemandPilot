# Tech Stack

| Layer | Choice | ADR |
|---|---|---|
| Language / runtime | Python 3.12+ | — |
| Dependency management | Poetry (+ poethepoet task runner) | — |
| Data storage/query | DuckDB | [001](adr/001-duckdb.md) |
| Dataframes | Polars (pandas only at library boundaries) | [007](adr/007-polars.md) |
| Forecasting model | LightGBM (quantile objective, direct multi-horizon) | [002](adr/002-lightgbm.md), [008](adr/008-direct-quantile-forecasting.md) |
| Inventory optimization | Newsvendor model | [003](adr/003-newsvendor.md), [012](adr/012-cost-coupled-quantiles.md) |
| Configuration | YAML + Pydantic v2 validation | [009](adr/009-pydantic-config.md) |
| Feature engineering | SQL generated from config via Jinja2 | [010](adr/010-config-generated-feature-sql.md) |
| Data versioning | Versioned DuckDB snapshots + manifest | [011](adr/011-snapshot-data-versioning.md) |
| Dataset | M5 (Walmart), Kaggle | [013](adr/013-m5-dataset.md) |
| Experiment tracking | MLflow (+ model registry) | [006](adr/006-mlflow.md) |
| App/UI | Streamlit | [004](adr/004-streamlit.md) |
| Report templating | Jinja2 | [005](adr/005-jinja2.md) |
| Visualization | Plotly | — |
| Scientific computing | NumPy, SciPy | — |
| Quality tooling | Black, Ruff, MyPy (strict), PyTest, pre-commit | — |
| CI/CD | GitHub Actions (3.12 + 3.13 matrix) | — |
| Containers | Docker multi-stage + compose (app, MLflow) | — |

See `adr/` for the rationale and trade-offs behind each choice.
