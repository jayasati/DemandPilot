-- Feature store view: joins sales, dimensions, calendar, and rolling features
-- into the table consumed by the forecasting pipeline. Column set mirrors
-- configs/features.yaml (generated from it starting in Volume 2).
--
-- snap_flag resolves the state-level SNAP indicator to the store's state.

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

    rf.units_sold_lag_1,
    rf.units_sold_lag_7,
    rf.units_sold_lag_14,
    rf.units_sold_lag_28,
    rf.units_sold_roll_mean_7,
    rf.units_sold_roll_std_7,
    rf.units_sold_roll_min_7,
    rf.units_sold_roll_max_7,
    rf.units_sold_roll_mean_14,
    rf.units_sold_roll_std_14,
    rf.units_sold_roll_min_14,
    rf.units_sold_roll_max_14,
    rf.units_sold_roll_mean_28,
    rf.units_sold_roll_std_28,
    rf.units_sold_roll_min_28,
    rf.units_sold_roll_max_28

FROM sales s
JOIN skus sk          ON sk.sku_id = s.sku_id
JOIN stores st        ON st.store_id = s.store_id
JOIN calendar c       ON c.date = s.date
LEFT JOIN rolling_features rf
    ON rf.store_id = s.store_id
   AND rf.sku_id = s.sku_id
   AND rf.date = s.date;
