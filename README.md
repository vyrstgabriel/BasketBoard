# Basketboard

Basketboard analyzes two years of real e-commerce transaction data from a UK-based online retailer, running product analytics workflows — churn, retention, cohort analysis, behavioral segmentation — with SQL as the primary analytical layer.

---

## Dataset

**Online Retail II** — UCI Machine Learning Repository.
1,067,371 transactions, Dec 2009 to Dec 2011. After removing anonymous transactions and cancellations: 5,878 identified customers, 37,033 orders.

---

## Key Findings

| Metric | Value |
|---|---|
| Overall churn rate (90-day) | 50.9% |
| Champion tier churn | 1.9% |
| Lost tier churn | 65.8% |
| One-time buyer retention | 22.5% |
| Repeat within 30 days retention | 65.3% |
| Returner retention vs non-returner | 61.9% vs 39.6% |
| Anonymous transaction share | 22.7% of transactions, 15.4% of revenue |

**Time to second purchase is the strongest retention predictor.** Customers who make a second purchase within 30 days retain at 65.3% vs 22.5% for one-time buyers. The second order is the moment a customer converts from "tried us once" to "has a habit."

**Returns signal engagement, not dissatisfaction.** Customers who made at least one return retain at 61.9% vs 39.6% and spend on average £5,784 vs £956 lifetime. Returners are the most engaged customers — they order frequently enough to occasionally be disappointed.

**Retention has a clear AHA threshold around order 4-5.** Retention climbs steeply from 22.5% (1 order) to 58.3% (5 orders), then levels off. The steepest gains are between orders 2-4, making that the highest-leverage window for CRM intervention.

**Anonymous transactions are a measurement gap.** 22.7% of all transactions can't be attributed to any customer, representing 15.4% of revenue. Average line value is lower for anonymous transactions (£13.68 vs £22.03), suggesting anonymous buyers skew toward smaller, impulse purchases.

---

## Project Structure

```
Basketboard/
├── queries/                             # the analytical core — SQL first
│   ├── 01_churn_by_rfm_segment.sql
│   ├── 02_cohort_retention_matrix.sql
│   ├── 03_dau_wau_trend.sql
│   ├── 04_time_to_second_purchase.sql
│   ├── 05_order_frequency_aha.sql
│   ├── 06_anonymous_transactions.sql
│   └── 07_returns_analysis.sql
├── results/                             # query output CSVs, read by dashboard
├── src/
│   ├── generate_data.py                 # not used (real data)
│   ├── load_db.py                       # clean CSV, engineer features, load SQLite
│   └── run_queries.py                   # execute queries/, save to results/
├── data/
│   ├── raw/                             # gitignored (place online_retail_II.csv here)
│   └── processed/
├── dashboard/
│   └── app.py                           # Streamlit, reads results/ only
└── requirements.txt
```

---

## Running It

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Place online_retail_II.csv in data/raw/
# (Download from: UCI Machine Learning Repository — Online Retail II)

# 3. Load and clean the data
python src/load_db.py

# 4. Run all queries
python src/run_queries.py

# 5. Launch dashboard
streamlit run dashboard/app.py
```

Steps 3-4 only need to run once. After that, only step 5 is needed.

---

## The Queries

Each query uses at least one of: CTE, window function, self-join, CASE WHEN, or strftime() bucketing.

| File | Question answered |
|---|---|
| 01_churn_by_rfm_segment.sql | Which RFM tiers churn most? Average revenue and orders per tier? |
| 02_cohort_retention_matrix.sql | How do monthly first-purchase cohorts retain over 12 months? |
| 03_dau_wau_trend.sql | How do daily purchasing customers, orders, and revenue trend over time? |
| 04_time_to_second_purchase.sql | Does time to second purchase predict long-term retention? |
| 05_order_frequency_aha.sql | Is there an order count where retention jumps (AHA moment)? |
| 06_anonymous_transactions.sql | What share of revenue is unattributable, and how do anonymous buyers differ? |
| 07_returns_analysis.sql | Do customers who make returns churn faster or slower? |

---

## Data Model

**transactions** — cleaned identified line items (805,549 rows)

| Column | Description |
|---|---|
| invoice | order identifier |
| customer_id | customer identifier |
| stock_code | product code |
| quantity | units purchased |
| invoice_date | timestamp |
| price | unit price (£) |
| revenue | quantity * price |
| country | customer country |

**customers** — one row per identified customer (5,878 rows)

| Column | Description |
|---|---|
| customer_id | unique identifier |
| country | most frequent country of purchase |
| first_order_date / last_order_date | purchase window |
| cohort_month | year-month of first purchase |
| frequency | total distinct orders |
| monetary | total spend (£) |
| recency_days | days since last purchase (relative to 2011-12-09) |
| r_score / f_score / m_score | RFM scores, 1-4 |
| rfm_tier | Champions / Loyal / New / At Risk / Lost |
| time_to_second_order_days | days between first and second purchase (NULL if never) |
| had_repeat_within_30d | 1 if second purchase within 30 days |
| churned | 1 if inactive 90+ days before 2011-12-09 |
| had_return | 1 if customer ever appeared on a cancellation invoice |

**RFM Tier Definitions**

| Tier | Rule | Interpretation |
|---|---|---|
| Champions | r >= 3 AND f >= 3 | Frequent buyers, still purchasing recently |
| Loyal | f >= 3 (any recency) | High frequency, may have gone quiet |
| New | r >= 3, f = 1 | Recent first-time buyer |
| At Risk | r <= 2, f >= 2 | Used to buy regularly, now lapsed |
| Lost | r <= 2, f = 1 | One-time buyer, not seen recently |

---

## Tech Stack

- **SQLite**: all analytical queries
- **Python**: data cleaning, feature engineering, DB loading, query execution
- **Streamlit + Plotly**: interactive dashboard
