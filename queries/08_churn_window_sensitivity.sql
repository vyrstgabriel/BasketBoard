-- Sensitivity of the no-purchase outcome to 90-day versus 180-day windows.
-- Cutoffs differ, so this is a robustness diagnostic rather than an
-- apples-to-apples causal comparison.

SELECT
    outcome_days,
    observation_end,
    outcome_end,
    COUNT(*) AS eligible_customers,
    SUM(churned_in_outcome) AS churned_customers,
    ROUND(AVG(churned_in_outcome) * 100, 1) AS churn_rate_pct
FROM customer_snapshot_sensitivity
GROUP BY outcome_days, observation_end, outcome_end
ORDER BY outcome_days;
