-- Does second-purchase timing during days 0-90 predict a later purchase?
--
-- Feature window: acquisition through day 90.
-- Outcome window: days 91-180 after acquisition.
-- Only customers with the full 180-day horizon are eligible. The first source
-- month is excluded to reduce left-censoring of pre-existing customers.

WITH params AS (
    SELECT
        date(MIN(order_date), 'start of month', '+1 month') AS first_valid_acquisition,
        MAX(order_date) AS dataset_end
    FROM orders
),

ranked_orders AS (
    SELECT
        customer_id,
        invoice,
        invoice_date,
        order_date,
        ROW_NUMBER() OVER (
            PARTITION BY customer_id
            ORDER BY invoice_date, invoice
        ) AS order_rank
    FROM orders
),

eligible AS (
    SELECT
        r.customer_id,
        r.order_date AS first_order_date
    FROM ranked_orders r
    CROSS JOIN params p
    WHERE r.order_rank = 1
      AND r.order_date >= p.first_valid_acquisition
      AND r.order_date <= date(p.dataset_end, '-180 days')
),

features AS (
    SELECT
        e.customer_id,
        e.first_order_date,
        CAST(
            julianday(s.order_date) - julianday(e.first_order_date)
        AS INTEGER) AS days_to_second_order
    FROM eligible e
    LEFT JOIN ranked_orders s
        ON e.customer_id = s.customer_id
       AND s.order_rank = 2
),

scored AS (
    SELECT
        f.customer_id,
        CASE
            WHEN f.days_to_second_order BETWEEN 0 AND 7 THEN 'Within 7 days'
            WHEN f.days_to_second_order BETWEEN 8 AND 30 THEN '8-30 days'
            WHEN f.days_to_second_order BETWEEN 31 AND 90 THEN '31-90 days'
            ELSE 'No second order in first 90 days'
        END AS second_purchase_timing,
        CASE
            WHEN f.days_to_second_order BETWEEN 0 AND 7 THEN 1
            WHEN f.days_to_second_order BETWEEN 8 AND 30 THEN 2
            WHEN f.days_to_second_order BETWEEN 31 AND 90 THEN 3
            ELSE 4
        END AS sort_order,
        CASE WHEN EXISTS (
            SELECT 1
            FROM orders o
            WHERE o.customer_id = f.customer_id
              AND o.order_date > date(f.first_order_date, '+90 days')
              AND o.order_date <= date(f.first_order_date, '+180 days')
        ) THEN 1 ELSE 0 END AS repeated_in_days_91_180
    FROM features f
)

SELECT
    second_purchase_timing,
    sort_order,
    COUNT(*) AS eligible_customers,
    SUM(repeated_in_days_91_180) AS later_repeat_customers,
    ROUND(AVG(repeated_in_days_91_180) * 100, 1) AS later_repeat_rate_pct,
    'Days 0-90 after first observed order' AS feature_window,
    'Days 91-180 after first observed order' AS outcome_window
FROM scored
GROUP BY second_purchase_timing, sort_order
ORDER BY sort_order;
