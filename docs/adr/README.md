# Architecture Decision Records

One record per significant architecture/technology decision. Format: Status /
Context / Decision / Consequences. New ADRs are written **before** the code
that implements them; superseded ADRs are marked, never deleted.

| # | Decision |
|---|---|
| [001](001-duckdb.md) | Use DuckDB for local/analytical data storage |
| [002](002-lightgbm.md) | Use LightGBM for demand forecasting |
| [003](003-newsvendor.md) | Use the newsvendor model for inventory optimization |
| [004](004-streamlit.md) | Use Streamlit for the app/UI layer |
| [005](005-jinja2.md) | Use Jinja2 for report and SQL templating |
| [006](006-mlflow.md) | Use MLflow for experiment tracking |
| [007](007-polars.md) | Use Polars for dataframe processing |
| [008](008-direct-quantile-forecasting.md) | Direct multi-horizon quantile forecasting (no recursion) |
| [009](009-pydantic-config.md) | Typed, fail-fast configuration with Pydantic |
| [010](010-config-generated-feature-sql.md) | Generate feature SQL from features.yaml |
| [011](011-snapshot-data-versioning.md) | Versioned feature snapshots as data versioning |
| [012](012-cost-coupled-quantiles.md) | Couple forecast quantiles to newsvendor economics |
| [013](013-m5-dataset.md) | Use the M5 (Walmart) dataset; fact-table ingestion policy |
| [014](014-future-known-vs-history-derived-features.md) | Direct multi-horizon assembly: future-known vs. history-derived features |
| [015](015-horizon-as-feature-training.md) | Horizon-as-feature training with origin sampling |
