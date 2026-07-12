-- Lag and rolling-window features over sales, keyed by (store_id, sku_id, date).
--
-- LEAKAGE RULE (ADR-008): no window may include the current row — its
-- units_sold is the prediction target. Rolling windows therefore end at
-- 1 PRECEDING and lags start at 1. Volume 2 replaces this hand-written view
-- with SQL generated from configs/features.yaml, with per-horizon shifts;
-- until then this file is the reference implementation and mirrors that config.

CREATE OR REPLACE VIEW rolling_features AS
SELECT
    store_id,
    sku_id,
    date,

    LAG(units_sold, 1)  OVER w AS units_sold_lag_1,
    LAG(units_sold, 7)  OVER w AS units_sold_lag_7,
    LAG(units_sold, 14) OVER w AS units_sold_lag_14,
    LAG(units_sold, 28) OVER w AS units_sold_lag_28,

    AVG(units_sold)    OVER (w ROWS BETWEEN 7 PRECEDING AND 1 PRECEDING) AS units_sold_roll_mean_7,
    STDDEV(units_sold) OVER (w ROWS BETWEEN 7 PRECEDING AND 1 PRECEDING) AS units_sold_roll_std_7,
    MIN(units_sold)    OVER (w ROWS BETWEEN 7 PRECEDING AND 1 PRECEDING) AS units_sold_roll_min_7,
    MAX(units_sold)    OVER (w ROWS BETWEEN 7 PRECEDING AND 1 PRECEDING) AS units_sold_roll_max_7,

    AVG(units_sold)    OVER (w ROWS BETWEEN 14 PRECEDING AND 1 PRECEDING) AS units_sold_roll_mean_14,
    STDDEV(units_sold) OVER (w ROWS BETWEEN 14 PRECEDING AND 1 PRECEDING) AS units_sold_roll_std_14,
    MIN(units_sold)    OVER (w ROWS BETWEEN 14 PRECEDING AND 1 PRECEDING) AS units_sold_roll_min_14,
    MAX(units_sold)    OVER (w ROWS BETWEEN 14 PRECEDING AND 1 PRECEDING) AS units_sold_roll_max_14,

    AVG(units_sold)    OVER (w ROWS BETWEEN 28 PRECEDING AND 1 PRECEDING) AS units_sold_roll_mean_28,
    STDDEV(units_sold) OVER (w ROWS BETWEEN 28 PRECEDING AND 1 PRECEDING) AS units_sold_roll_std_28,
    MIN(units_sold)    OVER (w ROWS BETWEEN 28 PRECEDING AND 1 PRECEDING) AS units_sold_roll_min_28,
    MAX(units_sold)    OVER (w ROWS BETWEEN 28 PRECEDING AND 1 PRECEDING) AS units_sold_roll_max_28

FROM sales
WINDOW w AS (PARTITION BY store_id, sku_id ORDER BY date);
