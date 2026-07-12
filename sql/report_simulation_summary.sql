-- Executive-report summary of the current simulation_results table (Volume 6):
-- one row per policy, aggregated across every replayed decision.

SELECT
    policy,
    COUNT(*)              AS n_decisions,
    SUM(cost)             AS total_cost,
    SUM(understock_cost)  AS total_understock_cost,
    SUM(overstock_cost)   AS total_overstock_cost,
    AVG(cost)             AS mean_cost
FROM simulation_results
GROUP BY policy
ORDER BY policy;
