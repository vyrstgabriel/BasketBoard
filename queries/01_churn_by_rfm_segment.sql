-- Future 90-day churn by RFM tier.
--
-- RFM features are calculated only from orders on or before observation_end.
-- Churn is then observed strictly afterward through outcome_end.

WITH tier_stats AS (
    SELECT
        observation_end,
        outcome_end,
        rfm_tier,
        COUNT(*)                                  AS total_customers,
        SUM(churned_in_outcome)                    AS churned_customers,
        ROUND(AVG(churned_in_outcome) * 100, 1)    AS churn_rate_pct,
        ROUND(AVG(monetary), 2)                   AS avg_gross_revenue_at_cutoff,
        ROUND(AVG(net_monetary), 2)               AS avg_net_revenue_at_cutoff,
        ROUND(SUM(monetary), 2)                   AS total_gross_revenue_at_cutoff,
        ROUND(SUM(net_monetary), 2)               AS total_net_revenue_at_cutoff,
        ROUND(AVG(frequency), 1)                  AS avg_orders_at_cutoff
    FROM customer_snapshot
    GROUP BY observation_end, outcome_end, rfm_tier
)

SELECT
    observation_end,
    outcome_end,
    rfm_tier,
    total_customers,
    churned_customers,
    churn_rate_pct,
    avg_gross_revenue_at_cutoff,
    avg_net_revenue_at_cutoff,
    total_gross_revenue_at_cutoff,
    total_net_revenue_at_cutoff,
    avg_orders_at_cutoff,
    CASE
        WHEN churn_rate_pct >= 80 THEN 'Critical'
        WHEN churn_rate_pct >= 60 THEN 'High'
        WHEN churn_rate_pct >= 40 THEN 'Moderate'
        ELSE 'Healthy'
    END AS risk_level
FROM tier_stats
ORDER BY churn_rate_pct DESC;
