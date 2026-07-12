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
- **Volume 2 — Feature engineering** ✅ (2026-07-12): `rolling_features` SQL
  generated from `configs/features.yaml` (ADR-010); versioned
  `feature_store_v{N}` snapshots with a lineage manifest (ADR-011); leakage
  test suite; `demandpilot build-features` CLI command.
  *Exit criterion met: snapshot built from config; leakage tests green.*
- **Volume 3 — Forecasting** ✅ (2026-07-12): direct multi-horizon dataset
  assembly with the future-known/history-derived feature split (ADR-014);
  horizon-as-feature quantile LightGBM with origin sampling (ADR-015);
  quantile-crossing correction; pinball/coverage/WAPE/bias/RMSE metrics;
  MLflow tracking (SQLite backend, ADR-006) + model registry;
  `demandpilot train` CLI command.
  *Exit criterion met on the test fixture: full assemble → chronological
  split → train → backtest → MLflow-log pipeline runs and produces sane
  metrics end-to-end. Not yet run against the real M5 dataset (not
  downloaded on this machine) — that remains a manual step for the user
  (docs/ENVIRONMENT_SETUP.md).*
- **Volume 4 — Optimization** ✅ (2026-07-12): `RecommendationBuilder` reuses
  Volume 3's assembly/training machinery to produce newsvendor order
  quantities (the critical-fractile forecast itself, ADR-012) with explicit
  cost rationale and safety-stock context, computed retrospectively at the
  most recent origin date with a known outcome (ADR-016); persisted to a
  `recommendations` table; `demandpilot recommend` CLI command.
  *Exit criterion met: recommendations per store/SKU reproducible from one
  command, on the test fixture — same real-vs-fixture-scale caveat as
  Volume 3.*
- **Volume 5 — Simulation** ✅ (2026-07-12): `SimulationEngine` replays the
  ML quantile policy against a classical baseline (Monte Carlo empirical /
  normal / Poisson order-up-to, ADR-017) across many held-out historical
  decision points, grading both against real outcomes in real currency
  (`core.newsvendor.realized_cost_breakdown`); persisted to a
  `simulation_results` table; `demandpilot simulate` CLI command.
  *Exit criterion met: policy comparison with a cost breakdown (understock
  vs. overstock, per policy) reproducible from one command, on the test
  fixture — same real-vs-fixture-scale caveat as Volumes 3–4.*
- **Volume 6 — Reporting** ✅ (2026-07-12): `ReportBuilder` gathers feature
  snapshot lineage, the latest MLflow backtest run, and the
  `recommendations`/`simulation_results` tables (each optional — every
  section degrades gracefully to a "run `demandpilot X`" prompt if its
  upstream command hasn't run yet) into a self-contained, dark-mode-aware
  executive HTML report; `demandpilot report` CLI command.
  *Exit criterion met: rendered end-to-end on the test fixture (verified by
  reading the actual output, not just asserting on substrings) with and
  without upstream data present.*

## Now

- **Volume 7 — Dashboard**: Streamlit app over read-only DuckDB connections.

## Later

- **Volume 8 — Hardening**: end-to-end Docker run, performance passes,
  documentation audit, KNOWN_LIMITATIONS review.

Future extensions beyond the roadmap are listed in
[KNOWN_LIMITATIONS.md](KNOWN_LIMITATIONS.md#future-extensions).
