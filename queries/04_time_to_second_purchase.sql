-- 04_time_to_second_purchase.sql
-- Primary behavioral analysis: does time-to-second-purchase predict
-- long-term retention?
--
-- WHY this metric: the second purchase is the moment a customer converts
-- from "tried us once" to "has a habit." Customers who return quickly are
-- far more likely to become long-term buyers. This is the e-commerce
-- equivalent of "Day-1 retention" in app analytics.
--
-- We bucket by how quickly customers made their second order, then compare
-- 90-day retention rates across buckets. Customers who never made a second
-- purchase are their own bucket ("One-time only").
--
-- Pattern: CASE WHEN for bucketing continuous values with a sort key.
-- The sort_order column means the dashboard can ORDER BY sort_order without
-- string-sorting the labels.

WITH bucketed AS (
    SELECT
        customer_id,
        churned,
        CASE
            WHEN made_second_purchase = 0               THEN 'One-time only'
            WHEN time_to_second_order_days <= 7         THEN 'Within 7 days'
            WHEN time_to_second_order_days <= 30        THEN '8-30 days'
            WHEN time_to_second_order_days <= 90        THEN '31-90 days'
            ELSE                                             '90+ days'
        END                                             AS repeat_bucket,
        CASE
            WHEN made_second_purchase = 0               THEN 1
            WHEN time_to_second_order_days <= 7         THEN 2
            WHEN time_to_second_order_days <= 30        THEN 3
            WHEN time_to_second_order_days <= 90        THEN 4
            ELSE                                             5
        END                                             AS sort_order
    FROM customers
)

SELECT
    repeat_bucket,
    sort_order,
    COUNT(*)                                AS total_customers,
    SUM(1 - churned)                        AS retained_customers,
    ROUND(AVG(1 - churned) * 100, 1)        AS retention_pct
FROM bucketed
GROUP BY repeat_bucket, sort_order
ORDER BY sort_order;
