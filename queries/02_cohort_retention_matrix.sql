-- Calendar-month cohort retention over the first 12 observed months.
--
-- The first source month is excluded because a first observed purchase at the
-- left edge is not necessarily a true acquisition. The final partial calendar
-- month is also excluded. Eligible zero-activity cells are emitted as zero;
-- future, right-censored cells are omitted and display as blank.

WITH RECURSIVE
params AS (
    SELECT
        date(MIN(order_date), 'start of month', '+1 month') AS first_valid_cohort,
        date(MAX(order_date), 'start of month', '-1 month') AS last_complete_month
    FROM orders
),

offsets(months_since_first) AS (
    SELECT 0
    UNION ALL
    SELECT months_since_first + 1
    FROM offsets
    WHERE months_since_first < 11
),

cohorts AS (
    SELECT c.customer_id, c.cohort_month
    FROM customers c
    CROSS JOIN params p
    WHERE date(c.cohort_month || '-01') >= p.first_valid_cohort
      AND date(c.cohort_month || '-01') <= p.last_complete_month
),

cohort_sizes AS (
    SELECT cohort_month, COUNT(*) AS cohort_size
    FROM cohorts
    GROUP BY cohort_month
),

eligible_cells AS (
    SELECT
        cs.cohort_month,
        cs.cohort_size,
        o.months_since_first
    FROM cohort_sizes cs
    CROSS JOIN offsets o
    CROSS JOIN params p
    WHERE date(
        cs.cohort_month || '-01',
        printf('+%d months', o.months_since_first)
    ) <= p.last_complete_month
),

activity AS (
    SELECT
        c.cohort_month,
        (
            (CAST(strftime('%Y', o.order_date) AS INTEGER)
             - CAST(substr(c.cohort_month, 1, 4) AS INTEGER)) * 12
            + CAST(strftime('%m', o.order_date) AS INTEGER)
            - CAST(substr(c.cohort_month, 6, 2) AS INTEGER)
        ) AS months_since_first,
        o.customer_id
    FROM orders o
    JOIN cohorts c ON o.customer_id = c.customer_id
    CROSS JOIN params p
    WHERE date(o.order_date, 'start of month') <= p.last_complete_month
),

retained AS (
    SELECT
        cohort_month,
        months_since_first,
        COUNT(DISTINCT customer_id) AS active_customers
    FROM activity
    WHERE months_since_first BETWEEN 0 AND 11
    GROUP BY cohort_month, months_since_first
)

SELECT
    e.cohort_month,
    e.cohort_size,
    e.months_since_first,
    COALESCE(r.active_customers, 0) AS active_customers,
    ROUND(
        100.0 * COALESCE(r.active_customers, 0) / e.cohort_size,
        1
    ) AS retention_pct
FROM eligible_cells e
LEFT JOIN retained r
    ON e.cohort_month = r.cohort_month
   AND e.months_since_first = r.months_since_first
ORDER BY e.cohort_month, e.months_since_first;
