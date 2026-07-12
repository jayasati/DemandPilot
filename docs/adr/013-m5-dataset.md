# 013. Use the M5 (Walmart) dataset; fact-table ingestion policy

## Status

Accepted (dataset choice approved by the project owner, 2026-07-11)

## Context

The project rules forbid fake data, so a real public retail dataset is
required. Candidates: M5 (Walmart — 3,049 items × 10 stores × 1,941 days,
hierarchical, with prices, SNAP days, and events), Kaggle Store-Item Demand
(small, synthetic-ish, no covariates), Favorita (larger but messier licensing).
M5 is the de-facto benchmark for retail probabilistic forecasting (the M5
Uncertainty competition scored exactly the quantile task this platform
performs), which makes results externally comparable.

## Decision

M5 Accuracy competition data (`sales_train_evaluation.csv`, `calendar.csv`,
`sell_prices.csv`), downloaded via `scripts/download_m5.py` (Kaggle
credentials + accepted rules required; the raw files are never committed).

Ingestion policy (implemented in `sql/ingest_m5.sql.j2`):

- Wide daily matrix is unpivoted in DuckDB to one row per (store, sku, date).
- Weekly prices join via `wm_yr_wk`; **rows before a SKU's first priced week
  are dropped** — M5 convention: the item was not yet on sale, and keeping
  structural zeros would bias the forecaster low. The drop count is logged and
  returned in `IngestionSummary`.
- `is_holiday` = event of type National/Religious; SNAP flags stay state-level
  in `calendar` (resolved to per-store `snap_flag` in the feature layer).
- **No PK/FK constraints on `sales`/`prices`**: DuckDB ART indexes on a ~59M-row
  fact make ingest memory-hungry for zero analytical benefit; integrity is
  enforced by the 13-check validation suite after every ingest.

## Consequences

- Real scale (~59M fact rows) keeps engineering honest; rich covariates feed
  the feature layer; benchmark comparability for Volume 3.
- Kaggle account friction for new contributors (mitigated: the test suite runs
  on deterministic fixtures, no dataset needed).
- Zero-demand days after launch remain censored (out-of-stock vs. no-demand is
  indistinguishable) — recorded in docs/KNOWN_LIMITATIONS.md.
