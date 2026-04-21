-- 05_order_frequency_aha.sql
-- Secondary behavioral analysis: is there an order count ("AHA moment")
-- after which retention jumps sharply?
--
-- WHY this matters: if retention jumps from 30% to 70% between customers
-- who placed 2 vs 3 lifetime orders, that's a clear product/CRM target —
-- get every customer to order #3. This is how companies like Amazon and
-- Shopify define activation thresholds.
--
-- We show retention rate at each order count 1-10, then 11+. The jump
-- point in the chart is the "magic number."
--
-- Pattern: CASE WHEN bucketing with a self-join on orders to count
-- how many orders each customer had placed up to a given point.
-- Here we use the customer's total order count as a proxy (lifetime frequency).

WITH order_counts AS (
    SELECT
        customer_id,
        churned,
        CASE
            WHEN frequency >= 11 THEN '11+'
            ELSE CAST(frequency AS TEXT)
        END                                     AS order_count_label,
        CASE
            WHEN frequency >= 11 THEN 11
            ELSE frequency
        END                                     AS sort_order
    FROM customers
)

SELECT
    order_count_label                           AS lifetime_orders,
    sort_order,
    COUNT(*)                                    AS total_customers,
    SUM(1 - churned)                            AS retained_customers,
    ROUND(AVG(1 - churned) * 100, 1)            AS retention_pct
FROM order_counts
GROUP BY order_count_label, sort_order
ORDER BY sort_order;
