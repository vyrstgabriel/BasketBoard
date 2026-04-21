-- 07_returns_analysis.sql
-- Bonus: do customers who make returns churn faster, or does returning
-- actually correlate with higher engagement?
--
-- WHY this is interesting: the intuitive answer is "returners are
-- dissatisfied and churn more." The data often says the opposite —
-- high-value, frequent customers also return more simply because they
-- order more. Surfacing this counterintuitive result shows analytical depth.
--
-- had_return is pre-computed in load_db.py: 1 if the customer ever appeared
-- on a cancellation invoice (Invoice starting with 'C'), else 0.
--
-- Pattern: CASE WHEN to label a binary flag, with aggregate comparison
-- across two groups. Simple but the insight it surfaces is non-obvious.

WITH return_groups AS (
    SELECT
        CASE WHEN had_return = 1 THEN 'Made a return' ELSE 'No returns' END
                                                AS returner_group,
        churned,
        monetary,
        frequency,
        rfm_tier
    FROM customers
)

SELECT
    returner_group,
    COUNT(*)                                    AS total_customers,
    SUM(1 - churned)                            AS retained_customers,
    ROUND(AVG(1 - churned) * 100, 1)            AS retention_pct,
    ROUND(AVG(monetary), 2)                     AS avg_lifetime_revenue,
    ROUND(AVG(CAST(frequency AS REAL)), 1)      AS avg_orders
FROM return_groups
GROUP BY returner_group
ORDER BY returner_group;
