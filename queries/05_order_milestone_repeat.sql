-- Next-90-day repeat rate after each observed order milestone.
--
-- Every milestone has a complete 90-day follow-up window. This is a temporal
-- association, not a causal estimate of the effect of placing another order.

WITH params AS (
    SELECT
        date(MIN(order_date), 'start of month', '+1 month') AS first_valid_acquisition,
        datetime(MAX(invoice_date), '-90 days') AS followup_cutoff
    FROM orders
),

ranked AS (
    SELECT
        customer_id,
        invoice,
        invoice_date,
        MIN(order_date) OVER (PARTITION BY customer_id) AS first_order_date,
        ROW_NUMBER() OVER (
            PARTITION BY customer_id
            ORDER BY invoice_date, invoice
        ) AS order_milestone,
        LEAD(invoice_date) OVER (
            PARTITION BY customer_id
            ORDER BY invoice_date, invoice
        ) AS next_order_timestamp
    FROM orders
),

eligible_milestones AS (
    SELECT
        r.customer_id,
        r.order_milestone,
        r.invoice_date AS milestone_timestamp,
        CASE
            WHEN r.next_order_timestamp <= datetime(r.invoice_date, '+90 days')
            THEN 1 ELSE 0
        END AS repeated_within_90d
    FROM ranked r
    CROSS JOIN params p
    WHERE r.first_order_date >= p.first_valid_acquisition
      AND r.order_milestone BETWEEN 1 AND 10
      AND r.invoice_date <= p.followup_cutoff
)

SELECT
    order_milestone,
    COUNT(*) AS eligible_customers,
    SUM(repeated_within_90d) AS repeated_within_90d,
    ROUND(AVG(repeated_within_90d) * 100, 1) AS repeat_rate_pct,
    'Purchase within 90 days after milestone' AS outcome_definition
FROM eligible_milestones
GROUP BY order_milestone
ORDER BY order_milestone;
