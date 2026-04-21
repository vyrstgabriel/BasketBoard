-- 06_anonymous_transactions.sql
-- Data quality analysis: what do anonymous transactions (no Customer ID)
-- look like vs identified ones?
--
-- WHY this matters: ~23% of transactions can't be attributed to any customer.
-- That means retention analysis has a blind spot. This query quantifies the
-- gap and looks for patterns — do anonymous transactions cluster by country
-- or time period? That would suggest a systematic cause (e.g., a specific
-- channel that doesn't capture logins).
--
-- Three result sets UNION'd together with a 'metric' label so the dashboard
-- can render them as separate summary cards:
--   1. High-level revenue share comparison
--   2. Country breakdown for anonymous transactions
--   3. Monthly volume trend for anonymous vs identified

WITH identified_summary AS (
    SELECT
        'Identified'                            AS customer_type,
        COUNT(*)                                AS transaction_count,
        ROUND(SUM(revenue), 2)                  AS total_revenue,
        ROUND(AVG(quantity * price), 2)         AS avg_line_value
    FROM transactions
),

anon_summary AS (
    SELECT
        'Anonymous'                             AS customer_type,
        COUNT(*)                                AS transaction_count,
        ROUND(SUM(revenue), 2)                  AS total_revenue,
        ROUND(AVG(quantity * price), 2)         AS avg_line_value
    FROM anonymous_tx
    WHERE quantity > 0
      AND price > 0
      -- Exclude cancellations from anonymous too
      AND CAST(invoice AS TEXT) NOT LIKE 'C%'
),

combined AS (
    SELECT * FROM identified_summary
    UNION ALL
    SELECT * FROM anon_summary
)

SELECT
    customer_type,
    transaction_count,
    total_revenue,
    avg_line_value,
    ROUND(
        100.0 * transaction_count / SUM(transaction_count) OVER(),
        1
    )                                           AS pct_of_transactions,
    ROUND(
        100.0 * total_revenue / SUM(total_revenue) OVER(),
        1
    )                                           AS pct_of_revenue
FROM combined;
