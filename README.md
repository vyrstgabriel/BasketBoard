# Basketboard

**E-commerce customer retention analytics with temporally valid outcomes**

**Live demo: [basketboard.streamlit.app](https://basketboard.streamlit.app/)**

Basketboard is a Streamlit and SQL portfolio project built on the
[UCI Online Retail II dataset](https://archive.ics.uci.edu/dataset/502/online%2Bretail%2Bii).
It focuses on a deceptively hard analytics question: do customer attributes
observed today predict purchasing behavior later?

The project intentionally separates feature windows from outcome windows,
guards against cohort censoring, distinguishes line items from orders, and
documents gross versus net revenue.

## Dataset and cleaning

Online Retail II contains 1,067,371 sales and cancellation line records from a
UK-based online retailer, spanning December 2009 through December 2011. The
source is Chen (2012), [DOI 10.24432/C5CG6D](https://doi.org/10.24432/C5CG6D),
and is licensed CC BY 4.0.

The pipeline applies these rules:

- Remove 34,335 exact duplicate source rows. The source has no line-item key,
  so rows identical across every supplied field are treated as duplicate
  ingestion.
- Separate anonymous lines before customer-level analysis.
- Exclude cancellation invoices and non-positive quantity or price from gross
  sales; retain identified cancellation lines separately for refund analysis.
- Aggregate each invoice to exactly one order, even when its lines have
  timestamps a few minutes apart.

The resulting identified sales model contains 779,425 line items, 36,969
invoice-level orders, and 5,878 customers.

## Defensible findings

| Finding | Result | Interpretation |
|---|---:|---|
| Future 90-day churn | 56.6% | 2,989 of 5,281 customers observed by Sep 10 made no purchase through Dec 9 |
| Champions vs Lost churn | 24.1% vs 81.3% | Pre-cutoff RFM tiers have strong—but not definitionally forced—future separation |
| Early second purchase | 55.2% vs 27.0% | Customers with a second order in days 0–90 were more likely to purchase in days 91–180 |
| Repeat after order 1 vs order 5 | 43.9% vs 68.2% | Higher observed milestones correlate with another purchase within 90 days |
| Anonymous measurement gap | 22.7% of lines, 7.8% of orders, 15.1% of gross revenue | Customer retention cannot be measured for anonymous orders |

These are predictive or descriptive associations, not causal estimates. In
particular, customers reaching later order milestones are a selected,
higher-engagement population; the chart does not establish an “AHA moment.”

### Churn window sensitivity

“Churn” is an operational no-purchase outcome, not proof that a customer has
permanently left.

| Outcome window | Feature cutoff | Eligible customers | No-purchase rate |
|---:|---|---:|---:|
| 90 days | 2011-09-10 | 5,281 | 56.6% |
| 180 days | 2011-06-12 | 4,977 | 48.2% |

The longer window includes a different seasonal period, so the comparison is a
sensitivity diagnostic rather than an apples-to-apples causal estimate.

## Analytical design

### RFM and future churn

RFM features use purchases on or before September 10, 2011. The outcome is
whether an eligible customer purchases during the following 90 days, ending
December 9, 2011.

R, F, and M all participate in the exhaustive tier mapping:

| Tier | Rule at the feature cutoff |
|---|---|
| Champions | Recent (`r >= 3`), frequent (`f >= 3`), and high monetary (`m >= 3`) |
| Loyal | Recent established customer not meeting all Champion thresholds |
| New | Recent customer with one observed order |
| At Risk | Stale (`r <= 2`) with high frequency (`f >= 3`) or monetary value (`m >= 3`) |
| Lost | Stale with lower frequency and monetary value |

### Calendar-month cohorts

The retention matrix uses calendar-month offsets rather than approximate
30-day bins. It excludes the first source month, where a first observed order
may belong to an existing customer, and the final partial month. Eligible
zero-activity cells appear as zero; future right-censored cells remain blank.

### Early repeat timing

For customers with a complete 180-day horizon:

- Feature: second-purchase timing during days 0–90 after first observed order.
- Outcome: any purchase during days 91–180.

The first source month is excluded to reduce left-censoring.

### Order milestones

For each observed order milestone 1–10, the query measures whether the next
order occurred within 90 days. A milestone is eligible only when its complete
follow-up window exists.

### Returns

Return status, order frequency, and revenue are measured before September 10;
retention is observed afterward. Returners and non-returners are compared
within pre-cutoff frequency bands because order frequency creates more
opportunities both to return and to remain active. Net revenue is gross positive
sales plus recorded negative cancellation value.

## Project structure

```text
Basketboard/
├── .streamlit/config.toml     # consistent hosted theme
├── dashboard/app.py
├── queries/
│   ├── 01_churn_by_rfm_segment.sql
│   ├── 02_cohort_retention_matrix.sql
│   ├── 03_dau_wau_trend.sql
│   ├── 04_time_to_second_purchase.sql
│   ├── 05_order_milestone_repeat.sql
│   ├── 06_anonymous_transactions.sql
│   ├── 07_returns_analysis.sql
│   └── 08_churn_window_sensitivity.sql
├── results/                 # versioned query outputs used by Streamlit
├── src/
│   ├── load_db.py           # cleaning, order grain, features, SQLite tables
│   └── run_queries.py       # SQL execution and CSV output
├── tests/test_pipeline.py
└── requirements.txt
```

## Data model

The generated SQLite database contains:

- `transactions`: deduplicated, identified, positive sales lines.
- `anonymous_tx`: deduplicated anonymous positive sales lines.
- `cancellations`: identified cancellation/refund lines with negative value.
- `orders`: one row per invoice.
- `customers`: full-history descriptive customer attributes.
- `customer_snapshot`: pre-cutoff RFM and return features plus the later outcome.
- `customer_snapshot_sensitivity`: reproducible 90- and 180-day scenarios.

## Run locally

```bash
pip install -r requirements.txt

# Place online_retail_II.csv in data/raw/, then:
python src/load_db.py
python src/run_queries.py
python -m unittest discover -s tests -v
streamlit run dashboard/app.py
```

The raw CSV and generated SQLite database are gitignored. Versioned result CSVs
allow the dashboard to run without shipping the source data.

## Limitations

- The source covers one retailer and is strongly seasonal.
- “First purchase” means first observed purchase; purchases before the source
  window are unavailable.
- Anonymous orders cannot enter customer-level retention analysis.
- Exact-row deduplication is a documented assumption because the source has no
  line-item identifier.
- Recorded cancellations are a practical refund proxy, not a fully reconciled
  accounting ledger.
- Gross billed revenue includes positive non-merchandise lines such as postage
  and manual adjustments; it is not a merchandise-only sales measure.
- RFM tiers and 90-day outcomes are analytical choices, not universal customer
  lifecycle definitions.
