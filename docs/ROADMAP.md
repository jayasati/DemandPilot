# Roadmap

Each volume follows the full lifecycle (planning → architecture →
implementation → testing → review → audit → documentation → merge) and has an
explicit exit criterion. No stage may be skipped.

## Done

- **Volume 0 — Foundation** ✅ (2026-07-12): git, Poetry, CI, Docker, pre-commit,
  typed config system, logging/exception strategies, full documentation set, ADRs.
- **Volume 1 — Data layer** ✅ (2026-07-12): M5 ingestion (unpivot + price join +
  launch filtering), star schema, 13-check validation suite, CLI.
  *Exit criterion met: real data queryable in DuckDB and validated.*

## Now

- **Volume 2 — Feature engineering**: generate the feature SQL from
  `configs/features.yaml` (ADR-010) with per-horizon shifts (ADR-008);
  versioned feature snapshots (ADR-011); automated leakage test suite.
  *Exit: snapshot built from config; leakage tests green.*

## Next

- **Volume 3 — Forecasting**: quantile LightGBM per quantile ∪ critical
  fractile; rolling-origin backtesting; pinball/coverage/WAPE/bias metrics;
  MLflow tracking + registry. *Exit: honest backtest report on real M5 data.*
- **Volume 4 — Optimization**: newsvendor order quantities with cost rationale.
  *Exit: recommendations per store/SKU reproducible from one command.*
- **Volume 5 — Simulation**: vectorized historical replay; baseline vs.
  optimized policy P&L. *Exit: policy comparison with cost breakdown.*

## Later

- **Volume 6 — Reporting**: Jinja2 executive reports (HTML).
- **Volume 7 — Dashboard**: Streamlit app over read-only DuckDB connections.
- **Volume 8 — Hardening**: end-to-end Docker run, performance passes,
  documentation audit, KNOWN_LIMITATIONS review.

Future extensions beyond the roadmap are listed in
[KNOWN_LIMITATIONS.md](KNOWN_LIMITATIONS.md#future-extensions).
