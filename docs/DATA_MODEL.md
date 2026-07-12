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

- `rolling_features` — leakage-safe lags/rolling windows (mirrors `configs/features.yaml`).
- `feature_store` — model-ready join of sales, dims, calendar, rolling features.
- `sales_summary` — daily totals by state/category for dashboards.
- `series_coverage` — first/last date and row count per (store, sku).
