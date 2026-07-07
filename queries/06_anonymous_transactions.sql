-- Measurement coverage for identified versus anonymous sales.
-- Line-item share and invoice/order share are reported separately.

WITH identified_orders AS (
    SELECT invoice, SUM(revenue) AS order_revenue
    FROM transactions
    GROUP BY invoice
),

anonymous_orders AS (
    SELECT invoice, SUM(revenue) AS order_revenue
    FROM anonymous_tx
    GROUP BY invoice
),

identified_summary AS (
    SELECT
        'Identified' AS customer_type,
        (SELECT COUNT(*) FROM transactions) AS line_item_count,
        COUNT(*) AS order_count,
        ROUND(SUM(order_revenue), 2) AS gross_revenue,
        ROUND((SELECT AVG(revenue) FROM transactions), 2) AS avg_line_value,
        ROUND(AVG(order_revenue), 2) AS avg_order_value
    FROM identified_orders
),

anonymous_summary AS (
    SELECT
        'Anonymous' AS customer_type,
        (SELECT COUNT(*) FROM anonymous_tx) AS line_item_count,
        COUNT(*) AS order_count,
        ROUND(SUM(order_revenue), 2) AS gross_revenue,
        ROUND((SELECT AVG(revenue) FROM anonymous_tx), 2) AS avg_line_value,
        ROUND(AVG(order_revenue), 2) AS avg_order_value
    FROM anonymous_orders
),

combined AS (
    SELECT * FROM identified_summary
    UNION ALL
    SELECT * FROM anonymous_summary
)

SELECT
    customer_type,
    line_item_count,
    order_count,
    gross_revenue,
    avg_line_value,
    avg_order_value,
    ROUND(100.0 * line_item_count / SUM(line_item_count) OVER(), 1) AS pct_line_items,
    ROUND(100.0 * order_count / SUM(order_count) OVER(), 1) AS pct_orders,
    ROUND(100.0 * gross_revenue / SUM(gross_revenue) OVER(), 1) AS pct_revenue
FROM combined;
