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
              [V3] horizon-aware dataset assembly (pair snapshot rows with
                   the target shifted by each horizon) → quantile LightGBM
                   (one model per quantile ∪ critical fractile) — MLflow-tracked
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

## Current command sequence (Volumes 0–2)

1. `demandpilot init-db` — applies `sql/create_tables.sql`,
   `sql/feature_snapshots.sql`, and `sql/views.sql`.
2. `demandpilot ingest-m5` — renders `sql/ingest_m5.sql.j2`, stages the CSVs,
   builds dimensions and the long sales fact, drops pre-launch rows, then runs
   the full validation suite and fails non-zero on any violation.
3. `demandpilot build-features` — generates `rolling_features` from
   `configs/features.yaml`, (re)creates `feature_store`, and materializes a new
   `feature_store_v{N}` snapshot with its lineage manifest row.
4. `demandpilot validate` — re-runs the validation suite on demand.

Every step logs to console and `logs/demandpilot.log`, reads all settings from
`configs/`, and is idempotent (re-running ingestion replaces the data).
