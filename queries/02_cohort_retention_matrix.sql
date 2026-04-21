-- 02_cohort_retention_matrix.sql
-- Monthly cohort retention: for each first-purchase-month cohort,
-- what % of customers made a purchase in months 1-12 after joining?
--
-- WHY monthly (not weekly): the dataset spans 2 years. Weekly cohorts
-- would produce ~100 rows on the heatmap and be unreadable. Monthly
-- gives 24 cohorts with enough customers per cell to be statistically
-- meaningful.
--
-- Pattern: three-CTE chain with a self-join between customers and orders.
--   1. cohorts    - each customer's cohort month and join date
--   2. activity   - for every order, months elapsed since first purchase
--   3. retained   - distinct active customers per cohort per month offset
--   Final join back to cohort sizes gives retention %.
--
-- strftime('%Y-%m', ...) truncates a date to year-month — SQLite's way
-- of "flooring to month."

WITH cohorts AS (
    SELECT
        customer_id,
        cohort_month,
        first_order_date
    FROM customers
),

activity AS (
    SELECT
        o.customer_id,
        c.cohort_month,
        -- Months elapsed: difference in months between order and first purchase.
        -- julianday difference / 30.44 gives approximate months; CAST to integer
        -- floors it so month 0 = same calendar month as signup.
        CAST(
            (julianday(o.order_date) - julianday(c.first_order_date)) / 30.44
        AS INTEGER)                             AS months_since_first
    FROM orders o
    JOIN cohorts c ON o.customer_id = c.customer_id
    WHERE CAST(
            (julianday(o.order_date) - julianday(c.first_order_date)) / 30.44
          AS INTEGER) BETWEEN 0 AND 11
),

cohort_sizes AS (
    SELECT cohort_month, COUNT(*) AS cohort_size
    FROM cohorts
    GROUP BY cohort_month
),

retained AS (
    SELECT
        cohort_month,
        months_since_first,
        COUNT(DISTINCT customer_id)     AS active_customers
    FROM activity
    GROUP BY cohort_month, months_since_first
)

SELECT
    r.cohort_month,
    cs.cohort_size,
    r.months_since_first,
    r.active_customers,
    ROUND(100.0 * r.active_customers / cs.cohort_size, 1)  AS retention_pct
FROM retained r
JOIN cohort_sizes cs ON r.cohort_month = cs.cohort_month
ORDER BY r.cohort_month, r.months_since_first;
