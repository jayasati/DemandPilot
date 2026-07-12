-- Feature store view: joins sales, dimensions, calendar, and the generated
-- rolling features (sql/rolling_features.sql.j2, ADR-010) into the model-ready
-- table. rf.* is selected wildcard-style (DuckDB EXCLUDE) so this view stays
-- valid whatever lag/window set configs/features.yaml specifies — no column
-- list to keep in sync by hand.
--
-- snap_flag resolves the state-level SNAP indicator to the store's state.
--
-- Requires rolling_features to already exist (DuckDB binds views eagerly) —
-- both are created together by demandpilot.features.FeatureSnapshotBuilder /
-- `demandpilot build-features`, never by the static schema in create_tables.sql.

CREATE OR REPLACE VIEW feature_store AS
SELECT
    s.store_id,
    s.sku_id,
    s.date,
    s.units_sold,
    s.sell_price,

    sk.dept_id,
    sk.cat_id,
    st.state_id,

    c.day_of_week,
    c.week_of_year,
    c.month,
    c.is_weekend,
    c.is_event,
    c.is_holiday,
    CASE st.state_id
        WHEN 'CA' THEN c.snap_ca
        WHEN 'TX' THEN c.snap_tx
        WHEN 'WI' THEN c.snap_wi
        ELSE FALSE
    END AS snap_flag,

    rf.* EXCLUDE (store_id, sku_id, date)

FROM sales s
JOIN skus sk          ON sk.sku_id = s.sku_id
JOIN stores st        ON st.store_id = s.store_id
JOIN calendar c       ON c.date = s.date
LEFT JOIN rolling_features rf
    ON rf.store_id = s.store_id
   AND rf.sku_id = s.sku_id
   AND rf.date = s.date;
