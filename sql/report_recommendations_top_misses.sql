-- Executive-report detail: the recommendations whose order quantity missed
-- realized demand by the largest absolute amount (most actionable content
-- for a summary — not a dump of every row). Capped at 20; the report
-- states the total count separately so this cap is never silent.

SELECT
    store_id,
    sku_id,
    origin_date,
    target_date,
    order_quantity,
    median_forecast,
    safety_stock,
    actual_demand,
    ABS(order_quantity - actual_demand) AS absolute_miss
FROM recommendations
ORDER BY absolute_miss DESC
LIMIT 20;
