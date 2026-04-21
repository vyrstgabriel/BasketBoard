-- 01_churn_by_rfm_segment.sql
-- Churn rate per RFM tier, ordered worst to best.
--
-- RFM tiers are pre-computed in load_db.py based on:
--   Recency (days since last purchase), Frequency (order count),
--   Monetary (total spend). Each scored 1-4; combined into named tiers.
--
-- Churn definition: no purchase in the 90 days before 2011-12-09.
--
-- Pattern: AVG on a 0/1 column = churn rate proportion.
-- CASE WHEN adds the churn label so the output is self-documenting.

WITH tier_stats AS (
    SELECT
        rfm_tier,
        COUNT(*)                            AS total_customers,
        SUM(churned)                        AS churned_customers,
        ROUND(AVG(churned) * 100, 1)        AS churn_rate_pct,
        ROUND(AVG(monetary), 2)             AS avg_revenue_per_customer,
        ROUND(AVG(frequency), 1)            AS avg_orders
    FROM customers
    GROUP BY rfm_tier
)

SELECT
    rfm_tier,
    total_customers,
    churned_customers,
    churn_rate_pct,
    avg_revenue_per_customer,
    avg_orders,
    CASE
        WHEN churn_rate_pct >= 80 THEN 'Critical'
        WHEN churn_rate_pct >= 50 THEN 'High'
        WHEN churn_rate_pct >= 25 THEN 'Moderate'
        ELSE 'Healthy'
    END AS risk_level
FROM tier_stats
ORDER BY churn_rate_pct DESC;
