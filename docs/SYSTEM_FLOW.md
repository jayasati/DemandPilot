# System Flow

## End-to-end pipeline

```
Kaggle M5 CSVs (scripts/download_m5.py)
      │
      ▼
[V1] ingest-m5 ──► DuckDB star schema (stores, skus, calendar, prices, sales)
      │                      │
      ▼                      ▼
[V1] validation suite   [V2] build-features: rolling_features SQL generated
  (13 integrity checks)      from configs/features.yaml (ADR-010), joined
      │                      into feature_store — leakage-safe (ends at
      │                      1 PRECEDING, valid for every horizon — ADR-008)
      │                      │
      │                      ▼
      │              versioned snapshot feature_store_v{N} + lineage
      │              manifest (git commit, config hash — ADR-011)
      │                      │
      ▼                      ▼
              [V3] self-join dataset assembly: history-derived features
                   from the ORIGIN row, calendar/price/dims from the TARGET
                   row (ADR-014); horizons 1..horizon_days stacked with
                   horizon as a feature + origin sampling (ADR-015)
                             │
                             ▼
              [V3] chronological split → one quantile LightGBM model per
                   quantile ∪ critical fractile, monotonic-corrected →
                   pinball/coverage/WAPE/bias/RMSE backtest — MLflow-tracked
                   (SQLite backend, model registry)
                             │
                             ▼
              P10/P50/P90 + fractile forecasts per (store, sku, date)
                             │
                             ▼
              [V4] recommend: retrain at the median + critical fractile on
                   the most recent origin with a known outcome (ADR-016);
                   Q* = the critical-fractile forecast; safety stock = Q* -
                   median; -> recommendations table (with actual_demand)
                             │
              ┌──────────────┼────────────────┐
              ▼              ▼                ▼
   [V5] policy          [V3] backtest    [V6] Jinja2
   simulation             report          executive reports
   (historical replay,  (pinball,              │
   P&L, extends V4)      coverage,              ▼
              │           WAPE, bias,      [V7] Streamlit
              │           RMSE)             dashboard
              └──────────────┴────────────────┘
```

## Current command sequence (Volumes 0–4)

1. `demandpilot init-db` — applies `sql/create_tables.sql`,
   `sql/feature_snapshots.sql`, and `sql/views.sql`.
2. `demandpilot ingest-m5` — renders `sql/ingest_m5.sql.j2`, stages the CSVs,
   builds dimensions and the long sales fact, drops pre-launch rows, then runs
   the full validation suite and fails non-zero on any violation.
3. `demandpilot build-features` — generates `rolling_features` from
   `configs/features.yaml`, (re)creates `feature_store`, and materializes a new
   `feature_store_v{N}` snapshot with its lineage manifest row.
4. `demandpilot train [--snapshot-version N]` — assembles the multi-horizon
   dataset from a snapshot (latest by default), splits chronologically,
   trains one LightGBM quantile model per quantile ∪ critical fractile,
   backtests on the held-out test set, and logs everything to MLflow.
5. `demandpilot recommend [--snapshot-version N] [--lead-time-days N]` —
   assembles a single-horizon dataset, trains median + critical-fractile
   models on everything before the most recent origin, predicts for that
   origin, and persists order-quantity recommendations (with realized
   `actual_demand`, since this is retrospective — ADR-016) to the
   `recommendations` table.
6. `demandpilot validate` — re-runs the validation suite on demand.

Every step logs to console and `logs/demandpilot.log`, reads all settings from
`configs/`, and is idempotent (re-running ingestion replaces the data).
