-- Future retention for pre-cutoff returners versus non-returners, stratified
-- by pre-cutoff order frequency to expose the major engagement confound.

WITH bucketed AS (
    SELECT
        observation_end,
        outcome_end,
        CASE
            WHEN frequency = 1 THEN '1 order'
            WHEN frequency BETWEEN 2 AND 3 THEN '2-3 orders'
            WHEN frequency BETWEEN 4 AND 7 THEN '4-7 orders'
            ELSE '8+ orders'
        END AS frequency_bucket,
        CASE
            WHEN frequency = 1 THEN 1
            WHEN frequency BETWEEN 2 AND 3 THEN 2
            WHEN frequency BETWEEN 4 AND 7 THEN 3
            ELSE 4
        END AS sort_order,
        CASE WHEN had_return = 1 THEN 'Made a return' ELSE 'No returns' END AS returner_group,
        retained_in_outcome,
        monetary,
        net_monetary
    FROM customer_snapshot
)

SELECT
    observation_end,
    outcome_end,
    frequency_bucket,
    sort_order,
    returner_group,
    COUNT(*) AS total_customers,
    SUM(retained_in_outcome) AS retained_customers,
    ROUND(AVG(retained_in_outcome) * 100, 1) AS retention_pct,
    ROUND(AVG(monetary), 2) AS avg_gross_revenue_at_cutoff,
    ROUND(AVG(net_monetary), 2) AS avg_net_revenue_at_cutoff
FROM bucketed
GROUP BY
    observation_end,
    outcome_end,
    frequency_bucket,
    sort_order,
    returner_group
ORDER BY sort_order, returner_group;
