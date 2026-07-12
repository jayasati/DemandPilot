-- Reporting/convenience views. Add new views here rather than embedding
-- ad-hoc SQL strings in Python.

-- Daily sales totals by state/category, for dashboard summaries.
CREATE OR REPLACE VIEW sales_summary AS
SELECT
    st.state_id,
    sk.cat_id,
    s.date,
    SUM(s.units_sold)                AS units_sold,
    SUM(s.units_sold * s.sell_price) AS revenue
FROM sales s
JOIN skus sk    ON sk.sku_id = s.sku_id
JOIN stores st  ON st.store_id = s.store_id
GROUP BY st.state_id, sk.cat_id, s.date;

-- Per-series coverage: first/last observed date and row count per (store, sku).
CREATE OR REPLACE VIEW series_coverage AS
SELECT
    store_id,
    sku_id,
    MIN(date)  AS first_date,
    MAX(date)  AS last_date,
    COUNT(*)   AS n_days
FROM sales
GROUP BY store_id, sku_id;
