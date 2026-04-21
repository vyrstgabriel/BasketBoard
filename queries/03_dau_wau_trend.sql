-- 03_dau_wau_trend.sql
-- Daily and weekly purchasing customers over the full observation window.
--
-- "Active" here means placed at least one order that day/week.
-- This is a purchasing-activity metric, not a login/session metric.
--
-- Pattern: UNION ALL of two GROUP BY levels with a granularity label.
-- The dashboard splits them with WHERE granularity = 'day'/'week',
-- keeping the query output as a single clean CSV.

WITH daily AS (
    SELECT
        order_date                              AS period,
        'day'                                   AS granularity,
        COUNT(DISTINCT customer_id)             AS active_customers,
        COUNT(DISTINCT invoice)                 AS orders_placed,
        ROUND(SUM(total_revenue), 2)            AS revenue
    FROM orders
    GROUP BY order_date
),

weekly AS (
    SELECT
        strftime('%Y-%W', order_date)           AS period,
        'week'                                  AS granularity,
        COUNT(DISTINCT customer_id)             AS active_customers,
        COUNT(DISTINCT invoice)                 AS orders_placed,
        ROUND(SUM(total_revenue), 2)            AS revenue
    FROM orders
    GROUP BY strftime('%Y-%W', order_date)
)

SELECT * FROM daily
UNION ALL
SELECT * FROM weekly
ORDER BY granularity, period;
