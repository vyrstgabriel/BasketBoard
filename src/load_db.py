"""
load_db.py — clean the Online Retail II dataset and load into SQLite.

Creates four tables:
  transactions   — cleaned, identified (Customer ID present) line items
  anonymous_tx   — line items with no Customer ID (kept for data quality analysis)
  orders         — one row per invoice: revenue, item count, date, customer
  customers      — one row per customer: RFM inputs + engineered features

Run: python src/load_db.py
"""

import sqlite3
import pandas as pd
import numpy as np
from pathlib import Path

ROOT    = Path(__file__).parent.parent
RAW_CSV = ROOT / "data" / "raw" / "online_retail_II.csv"
DB_PATH = ROOT / "data" / "basketboard.db"

DATASET_END   = pd.Timestamp("2011-12-09")
CHURN_DAYS    = 90   # no purchase in 90 days before dataset end = churned


def load_raw() -> pd.DataFrame:
    df = pd.read_csv(RAW_CSV, encoding="latin-1", dtype={"Invoice": str},
                     parse_dates=["InvoiceDate"])
    df.columns = ["invoice", "stock_code", "description", "quantity",
                  "invoice_date", "price", "customer_id", "country"]
    return df


def split_anonymous(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Separate rows with and without a Customer ID."""
    anon       = df[df["customer_id"].isna()].copy()
    identified = df[df["customer_id"].notna()].copy()
    identified["customer_id"] = identified["customer_id"].astype(int).astype(str)
    return identified, anon


def extract_cancellations(df: pd.DataFrame) -> pd.DataFrame:
    """Return rows that are cancellations (Invoice starts with C)."""
    mask = df["invoice"].astype(str).str.startswith("C")
    c = df[mask & (df["quantity"] < 0)].copy()
    c["revenue"] = c["quantity"] * c["price"]   # negative value = returned amount
    return c.reset_index(drop=True)


def clean_transactions(df: pd.DataFrame) -> pd.DataFrame:
    """Remove cancellations, bad prices, and zero/negative quantities."""
    df = df[~df["invoice"].astype(str).str.startswith("C")]
    df = df[df["quantity"] > 0]
    df = df[df["price"] > 0]
    df = df.copy()
    df["revenue"] = df["quantity"] * df["price"]
    return df.reset_index(drop=True)


def build_orders(tx: pd.DataFrame) -> pd.DataFrame:
    """Aggregate to invoice level: one row per order."""
    orders = (
        tx.groupby(["invoice", "customer_id", "invoice_date", "country"])
        .agg(
            total_items   = ("quantity", "sum"),
            total_revenue = ("revenue",  "sum"),
            unique_products = ("stock_code", "nunique"),
        )
        .reset_index()
    )
    orders["invoice_date"] = pd.to_datetime(orders["invoice_date"])
    orders["order_date"] = orders["invoice_date"].dt.normalize()
    return orders


def build_customers(orders: pd.DataFrame) -> pd.DataFrame:
    """
    One row per customer with:
      - first/last order dates, cohort month
      - RFM inputs (recency_days, frequency, monetary)
      - time_to_second_order_days (NULL if only 1 order)
      - had_repeat_within_30d flag
      - churned flag (no purchase in 90 days before dataset end)
    """
    # Rank each order per customer by date to find 1st and 2nd purchase
    orders_sorted = orders.sort_values(["customer_id", "order_date"]).copy()
    orders_sorted["order_rank"] = (
        orders_sorted.groupby("customer_id")["order_date"]
        .rank(method="first").astype(int)
    )
    first = (
        orders_sorted[orders_sorted["order_rank"] == 1]
        [["customer_id", "order_date"]].rename(columns={"order_date": "first_order_date"})
    )
    second = (
        orders_sorted[orders_sorted["order_rank"] == 2]
        [["customer_id", "order_date"]].rename(columns={"order_date": "second_order_date"})
    )

    cust = (
        orders.groupby("customer_id")
        .agg(
            last_order_date  = ("order_date",    "max"),
            total_orders     = ("invoice",       "nunique"),
            total_revenue    = ("total_revenue", "sum"),
            total_items      = ("total_items",   "sum"),
            country          = ("country",       lambda x: x.mode()[0]),
        )
        .reset_index()
    )

    cust = cust.merge(first,  on="customer_id", how="left")
    cust = cust.merge(second, on="customer_id", how="left")

    # Cohort = year-month of first order
    cust["cohort_month"] = cust["first_order_date"].dt.to_period("M").astype(str)

    # RFM inputs
    cust["recency_days"] = (DATASET_END - cust["last_order_date"]).dt.days
    cust["frequency"]    = cust["total_orders"]
    cust["monetary"]     = cust["total_revenue"].round(2)

    # Time to second purchase
    cust["time_to_second_order_days"] = (
        (cust["second_order_date"] - cust["first_order_date"]).dt.days
    )
    cust["had_repeat_within_30d"] = (
        cust["time_to_second_order_days"].notna() &
        (cust["time_to_second_order_days"] <= 30)
    ).astype(int)
    cust["made_second_purchase"] = cust["second_order_date"].notna().astype(int)

    # Churn: no purchase in the 90 days before dataset end
    cust["churned"] = (cust["recency_days"] > CHURN_DAYS).astype(int)

    # RFM scoring: 1-4 scale per dimension.
    #
    # Recency + Monetary: quartile-based (continuous distributions, qcut works).
    # Recency is inverted — fewer days since last purchase = higher score.
    #
    # Frequency: fixed thresholds, because this retail dataset is heavily
    # right-skewed (~28% of customers bought only once). qcut would collapse
    # nearly everyone into score=1, making the dimension useless.
    #   1 order -> 1 | 2-3 -> 2 | 4-7 -> 3 | 8+ -> 4
    cust["r_score"] = pd.qcut(cust["recency_days"], q=4,
                               labels=[4, 3, 2, 1], duplicates="drop").astype(int)
    cust["m_score"] = pd.qcut(cust["monetary"],     q=4,
                               labels=[1, 2, 3, 4], duplicates="drop").astype(int)
    cust["f_score"] = pd.cut(
        cust["frequency"],
        bins=[0, 1, 3, 7, np.inf],
        labels=[1, 2, 3, 4],
        right=True,
    ).astype(int)

    # RFM tier labels
    def rfm_tier(row):
        r, f, m = row["r_score"], row["f_score"], row["m_score"]
        if r >= 3 and f >= 3:
            return "Champions"
        elif f >= 3:
            return "Loyal"
        elif r >= 3 and f == 1:
            return "New"
        elif r <= 2 and f >= 2:
            return "At Risk"
        else:
            return "Lost"

    cust["rfm_tier"] = cust.apply(rfm_tier, axis=1)

    return cust.drop(columns=["second_order_date"])


def add_return_flag(customers: pd.DataFrame, cancellations: pd.DataFrame) -> pd.DataFrame:
    """Flag customers who made at least one return."""
    returners = set(cancellations["customer_id"].dropna().astype(str).unique())
    customers = customers.copy()
    customers["had_return"] = customers["customer_id"].isin(returners).astype(int)
    return customers


def load():
    print("Reading CSV...")
    raw = load_raw()
    print(f"  {len(raw):,} rows total")

    identified, anon = split_anonymous(raw)
    print(f"  {len(identified):,} identified  |  {len(anon):,} anonymous")

    cancellations = extract_cancellations(identified)
    tx            = clean_transactions(identified)
    print(f"  {len(tx):,} clean transactions  |  {len(cancellations):,} cancellation lines")

    orders    = build_orders(tx)
    customers = build_customers(orders)
    customers = add_return_flag(customers, cancellations)
    print(f"  {orders['customer_id'].nunique():,} customers  |  {len(orders):,} orders")

    anon = anon.copy()
    anon["revenue"] = anon["quantity"] * anon["price"]

    con = sqlite3.connect(DB_PATH)
    tx.to_sql("transactions",  con, if_exists="replace", index=False)
    anon.to_sql("anonymous_tx", con, if_exists="replace", index=False)
    cancellations.to_sql("cancellations", con, if_exists="replace", index=False)
    orders.to_sql("orders",    con, if_exists="replace", index=False)
    customers.to_sql("customers", con, if_exists="replace", index=False)
    con.close()

    print(f"\nLoaded 5 tables into {DB_PATH}")
    print(f"  RFM tier breakdown:\n{customers['rfm_tier'].value_counts().to_string()}")
    print(f"  Churn rate: {customers['churned'].mean():.1%}")


if __name__ == "__main__":
    load()
