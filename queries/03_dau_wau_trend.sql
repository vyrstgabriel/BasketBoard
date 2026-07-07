-- Daily and weekly purchasing activity over the complete source window.
-- Daily output includes zero-order calendar days so averages and gaps are not
-- biased toward active sales days.

WITH RECURSIVE
params AS (
    SELECT date(MIN(order_date)) AS min_date, date(MAX(order_date)) AS max_date
    FROM orders
),

calendar(period) AS (
    SELECT min_date FROM params
    UNION ALL
    SELECT date(period, '+1 day')
    FROM calendar, params
    WHERE period < max_date
),

daily_stats AS (
    SELECT
        date(order_date) AS period,
        COUNT(DISTINCT customer_id) AS active_customers,
        COUNT(*) AS orders_placed,
        ROUND(SUM(total_revenue), 2) AS gross_revenue
    FROM orders
    GROUP BY date(order_date)
),

daily AS (
    SELECT
        c.period,
        'day' AS granularity,
        COALESCE(d.active_customers, 0) AS active_customers,
        COALESCE(d.orders_placed, 0) AS orders_placed,
        COALESCE(d.gross_revenue, 0) AS gross_revenue
    FROM calendar c
    LEFT JOIN daily_stats d ON c.period = d.period
),

weekly AS (
    SELECT
        date(
            date(order_date),
            printf('-%d days', (CAST(strftime('%w', date(order_date)) AS INTEGER) + 6) % 7)
        ) AS period,
        'week' AS granularity,
        COUNT(DISTINCT customer_id) AS active_customers,
        COUNT(*) AS orders_placed,
        ROUND(SUM(total_revenue), 2) AS gross_revenue
    FROM orders
    GROUP BY period
)

SELECT * FROM daily
UNION ALL
SELECT * FROM weekly
ORDER BY granularity, period;
