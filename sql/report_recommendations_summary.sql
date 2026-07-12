-- Executive-report summary of the current recommendations table (Volume 6).
-- Read-only; assumes the caller has already checked the table exists.

SELECT
    COUNT(*)                AS n_recommendations,
    MIN(origin_date)        AS recommendation_date,
    MAX(lead_time_days)     AS lead_time_days,
    SUM(order_quantity)     AS total_order_quantity,
    SUM(safety_stock)       AS total_safety_stock,
    MIN(critical_fractile)  AS critical_fractile,  -- constant across one run
    MAX(snapshot_table)     AS snapshot_table
FROM recommendations;
