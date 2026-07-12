-- Base tables for DemandPilot (DuckDB). Schema documented in docs/DATA_MODEL.md.
--
-- Dimension tables carry PK constraints. The sales fact table deliberately has
-- no PK/FK constraints: at M5 scale (~59M rows) DuckDB's ART index makes the
-- ingest memory-hungry for no query benefit. Integrity is enforced by the
-- validation suite instead (demandpilot.data.validation, ADR-013).

CREATE TABLE IF NOT EXISTS stores (
    store_id    VARCHAR PRIMARY KEY,
    state_id    VARCHAR NOT NULL
);

CREATE TABLE IF NOT EXISTS skus (
    sku_id      VARCHAR PRIMARY KEY,
    dept_id     VARCHAR NOT NULL,
    cat_id      VARCHAR NOT NULL
);

CREATE TABLE IF NOT EXISTS calendar (
    date            DATE PRIMARY KEY,
    d               VARCHAR NOT NULL UNIQUE,   -- M5 day key: d_1 = 2011-01-29
    wm_yr_wk        INTEGER NOT NULL,          -- Walmart week key (joins prices)
    day_of_week     TINYINT NOT NULL,          -- 0 = Sunday .. 6 = Saturday
    week_of_year    TINYINT NOT NULL,
    month           TINYINT NOT NULL,
    year            SMALLINT NOT NULL,
    is_weekend      BOOLEAN NOT NULL,
    event_name_1    VARCHAR,
    event_type_1    VARCHAR,
    event_name_2    VARCHAR,
    event_type_2    VARCHAR,
    is_event        BOOLEAN NOT NULL,
    is_holiday      BOOLEAN NOT NULL,          -- event of type National or Religious
    snap_ca         BOOLEAN NOT NULL,
    snap_tx         BOOLEAN NOT NULL,
    snap_wi         BOOLEAN NOT NULL
);

-- Weekly sell prices; a (store, sku) appears only from its launch week onward.
CREATE TABLE IF NOT EXISTS prices (
    store_id    VARCHAR NOT NULL,
    sku_id      VARCHAR NOT NULL,
    wm_yr_wk    INTEGER NOT NULL,
    sell_price  DOUBLE NOT NULL
);

-- Sales fact: one row per (store, sku, date), starting at the SKU's launch.
CREATE TABLE IF NOT EXISTS sales (
    store_id    VARCHAR NOT NULL,
    sku_id      VARCHAR NOT NULL,
    date        DATE NOT NULL,
    units_sold  INTEGER NOT NULL,
    sell_price  DOUBLE NOT NULL
);
