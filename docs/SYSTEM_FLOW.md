# System Flow

## End-to-end pipeline

```
Kaggle M5 CSVs (scripts/download_m5.py)
      │
      ▼
[V1] ingest-m5 ──► DuckDB star schema (stores, skus, calendar, prices, sales)
      │                      │
      ▼                      ▼
[V1] validation suite   [V2] feature SQL generated from configs/features.yaml
  (13 integrity checks)      │  horizon-shifted lags/windows — leakage-safe
      │                      ▼
      │              versioned feature snapshot (data/snapshots, ADR-011)
      │                      │
      ▼                      ▼
              [V3] quantile LightGBM (direct multi-horizon, one model
                   per quantile ∪ critical fractile) — tracked in MLflow
                             │
                             ▼
              P10/P50/P90 + fractile forecasts per (store, sku, date)
                             │
              ┌──────────────┼────────────────┐
              ▼              ▼                ▼
   [V4] newsvendor     [V5] policy      [V3] backtest report
   order quantities    simulation        (pinball, coverage,
   + cost rationale    (historical        WAPE, bias, RMSE)
              │         replay, P&L)          │
              └──────────────┼────────────────┘
                             ▼
        [V6] Jinja2 executive reports   [V7] Streamlit dashboard
```

## Current command sequence (Volumes 0–1)

1. `demandpilot init-db` — applies `sql/create_tables.sql` and the views.
2. `demandpilot ingest-m5` — renders `sql/ingest_m5.sql.j2`, stages the CSVs,
   builds dimensions and the long sales fact, drops pre-launch rows, then runs
   the full validation suite and fails non-zero on any violation.
3. `demandpilot validate` — re-runs the validation suite on demand.

Every step logs to console and `logs/demandpilot.log`, reads all settings from
`configs/`, and is idempotent (re-running ingestion replaces the data).
