# Data Model

Star schema in DuckDB, populated from the M5 dataset (DDL:
`sql/create_tables.sql`; ingestion: `sql/ingest_m5.sql.j2`).

## Entities

```
stores ─────┐
            ├──< sales >── calendar
skus ───────┘        │
                     └── prices (weekly, via calendar.wm_yr_wk)
```

### `stores` (10 rows)
| column | type | notes |
|---|---|---|
| store_id | VARCHAR PK | e.g. `CA_1` |
| state_id | VARCHAR | `CA` / `TX` / `WI` |

### `skus` (3,049 rows)
| column | type | notes |
|---|---|---|
| sku_id | VARCHAR PK | M5 `item_id`, e.g. `FOODS_3_090` |
| dept_id | VARCHAR | e.g. `FOODS_3` |
| cat_id | VARCHAR | `FOODS` / `HOBBIES` / `HOUSEHOLD` |

### `calendar` (1,969 rows)
| column | type | notes |
|---|---|---|
| date | DATE PK | |
| d | VARCHAR UNIQUE | M5 day key; `d_1` = 2011-01-29 |
| wm_yr_wk | INTEGER | Walmart week key — joins `prices` |
| day_of_week..year, is_weekend | | derived from `date` (0 = Sunday) |
| event_name/type_1, _2 | VARCHAR | M5 events (nullable) |
| is_event | BOOLEAN | any event that day |
| is_holiday | BOOLEAN | event of type `National` or `Religious` |
| snap_ca / snap_tx / snap_wi | BOOLEAN | SNAP food-stamp days per state |

### `prices` (~6.8M rows)
Weekly sell price per (store_id, sku_id, wm_yr_wk). A pair appears only from
its launch week onward. Logical key: (store_id, sku_id, wm_yr_wk).

### `sales` (~59M rows before launch-filtering)
One row per (store_id, sku_id, date) from the SKU's launch at that store.
Columns: `units_sold INTEGER`, `sell_price DOUBLE` (the week's price).

## Design decisions

- **No PK/FK constraints on the facts** (`sales`, `prices`): DuckDB's ART index
  makes constrained inserts memory-hungry at ~59M rows and buys nothing for
  analytical queries. Integrity is enforced by the 13-check validation suite
  in `demandpilot.data.validation` after every ingest (ADR-013).
- **Pre-launch rows are dropped, not zero-filled**: before a SKU's first priced
  week the item was not on sale, so those zeros are not demand observations.
  Keeping them would bias the forecaster toward zero (ADR-013).
- **SNAP stays state-level in `calendar`**: the feature layer resolves it to a
  per-store `snap_flag` (see `sql/feature_store.sql`) instead of denormalizing
  59M boolean values into the fact table.
- **No inventory table yet**: M5 has no inventory positions; simulated
  inventory state is produced (not stored) by the Volume 5 engine.

## Views

- `rolling_features` — leakage-safe lags/rolling windows, **generated** from
  `configs/features.yaml` by `demandpilot.features.FeatureSqlGenerator`
  (ADR-010). Created by `demandpilot build-features`, not by `init-db` — DuckDB
  binds views eagerly, so this only exists once that command has run.
- `feature_store` — model-ready join of sales, dims, calendar, and
  `rolling_features` (`rf.* EXCLUDE (store_id, sku_id, date)`, so it needs no
  edits when the lag/window set changes). Also created by `build-features`.
- `sales_summary` — daily totals by state/category for dashboards.
- `series_coverage` — first/last date and row count per (store, sku).

## Feature snapshots (ADR-011)

`demandpilot build-features` also materializes the current `feature_store`
view into a versioned table and records its lineage:

### `feature_snapshots` (manifest)
| column | type | notes |
|---|---|---|
| version | INTEGER PK | auto-increments from `MAX(version) + 1` |
| table_name | VARCHAR UNIQUE | e.g. `feature_store_v3` |
| created_at | TIMESTAMP | UTC |
| git_commit | VARCHAR | `git rev-parse HEAD` at build time; NULL if git unavailable |
| config_hash | VARCHAR | SHA-256 of the resolved `FeaturesConfig`, truncated to 16 hex chars |
| row_count | BIGINT | rows in the snapshot table |
| min_date / max_date | DATE | date range covered |

### `feature_store_v{N}` (snapshot tables)
Full materialization of `feature_store` at build time — one per call to
`build-features`. Volume 3 trains only against a named snapshot, never the
live view, so training data is always reproducible.

## Recommendations (Volume 4)

### `recommendations`
Written by `demandpilot recommend` (`demandpilot.optimization.
persist_recommendations`); **always fully replaced**, not versioned like
feature snapshots — a live operational output refreshed on each run, not a
training artifact needing historical reproducibility (ADR-016). Schema is
inferred from `Recommendation`'s fields, not hand-declared, so it can't drift:

| column | notes |
|---|---|
| store_id, sku_id | series key |
| origin_date, target_date | `target_date = origin_date + lead_time_days` |
| lead_time_days | horizon recommended for |
| order_quantity | `Q*` — the critical-fractile demand forecast |
| median_forecast | P50 forecast, for context |
| safety_stock | `order_quantity - median_forecast` (can be negative) |
| critical_fractile, understock_cost_ratio, overstock_cost_ratio | cost rationale (ADR-012) |
| actual_demand | realized outcome at `target_date` — recommendations are retrospective (ADR-016) |
| snapshot_table | which `feature_store_v{N}` this run used |
