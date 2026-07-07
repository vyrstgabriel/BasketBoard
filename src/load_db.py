"""
Clean Online Retail II and load analysis-ready tables into SQLite.

The pipeline deliberately separates customer features from future outcomes:

* ``customers`` contains full-history descriptive customer attributes.
* ``customer_snapshot`` contains RFM features known at OBSERVATION_END and a
  90-day outcome observed strictly after that date.

Run: python src/load_db.py
"""

from pathlib import Path
import sqlite3

import numpy as np
import pandas as pd


ROOT = Path(__file__).parent.parent
RAW_CSV = ROOT / "data" / "raw" / "online_retail_II.csv"
DB_PATH = ROOT / "data" / "basketboard.db"

# The source ends on this date. Keeping it explicit makes every published
# result reproducible instead of silently changing with a different extract.
DATASET_END = pd.Timestamp("2011-12-09")
OUTCOME_DAYS = 90
OBSERVATION_END = DATASET_END - pd.Timedelta(days=OUTCOME_DAYS)
SENSITIVITY_WINDOWS = (90, 180)


def load_raw(path: Path = RAW_CSV) -> pd.DataFrame:
    df = pd.read_csv(
        path,
        encoding="latin-1",
        dtype={"Invoice": str},
        parse_dates=["InvoiceDate"],
    )
    df.columns = [
        "invoice",
        "stock_code",
        "description",
        "quantity",
        "invoice_date",
        "price",
        "customer_id",
        "country",
    ]
    return df


def drop_exact_duplicates(df: pd.DataFrame) -> tuple[pd.DataFrame, int]:
    """Remove exact source-row duplicates and return the number removed.

    Online Retail II has no line-item identifier. Exact copies across every
    supplied column cannot be distinguished as separate items, so the pipeline
    treats them as duplicate ingestion and documents the rule explicitly.
    """
    duplicate_count = int(df.duplicated().sum())
    return df.drop_duplicates().reset_index(drop=True), duplicate_count


def split_anonymous(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Separate rows with and without a customer identifier."""
    anonymous = df[df["customer_id"].isna()].copy()
    identified = df[df["customer_id"].notna()].copy()
    identified["customer_id"] = identified["customer_id"].astype(int).astype(str)
    return identified, anonymous


def extract_cancellations(df: pd.DataFrame) -> pd.DataFrame:
    """Return identified cancellation lines with negative refund value."""
    mask = df["invoice"].astype(str).str.startswith("C")
    cancellations = df[mask & (df["quantity"] < 0)].copy()
    cancellations["revenue"] = cancellations["quantity"] * cancellations["price"]
    return cancellations.reset_index(drop=True)


def clean_transactions(df: pd.DataFrame) -> pd.DataFrame:
    """Keep positive, non-cancelled sales lines and calculate gross revenue."""
    cleaned = df[~df["invoice"].astype(str).str.startswith("C")]
    cleaned = cleaned[(cleaned["quantity"] > 0) & (cleaned["price"] > 0)].copy()
    cleaned["revenue"] = cleaned["quantity"] * cleaned["price"]
    return cleaned.reset_index(drop=True)


def build_orders(tx: pd.DataFrame) -> pd.DataFrame:
    """Aggregate sales lines to exactly one row per invoice.

    Some invoices have lines timestamped one or two minutes apart. Invoice is
    the order identifier, so timestamp is aggregated rather than used as part
    of the grouping key.
    """
    invoice_integrity = tx.groupby("invoice").agg(
        customers=("customer_id", "nunique"),
        countries=("country", "nunique"),
    )
    if (invoice_integrity[["customers", "countries"]] > 1).any().any():
        raise ValueError("An invoice maps to multiple customers or countries")

    orders = (
        tx.groupby(["invoice", "customer_id", "country"], as_index=False)
        .agg(
            invoice_date=("invoice_date", "min"),
            last_line_timestamp=("invoice_date", "max"),
            total_items=("quantity", "sum"),
            total_revenue=("revenue", "sum"),
            unique_products=("stock_code", "nunique"),
            line_items=("stock_code", "size"),
        )
    )
    orders["invoice_date"] = pd.to_datetime(orders["invoice_date"])
    orders["last_line_timestamp"] = pd.to_datetime(orders["last_line_timestamp"])
    orders["order_date"] = orders["invoice_date"].dt.normalize()
    return orders


def build_customers(orders: pd.DataFrame) -> pd.DataFrame:
    """Build full-history descriptive customer attributes."""
    ordered = orders.sort_values(["customer_id", "invoice_date", "invoice"]).copy()
    ordered["order_rank"] = ordered.groupby("customer_id").cumcount() + 1

    first = ordered[ordered["order_rank"] == 1][
        ["customer_id", "order_date"]
    ].rename(columns={"order_date": "first_order_date"})
    second = ordered[ordered["order_rank"] == 2][
        ["customer_id", "order_date"]
    ].rename(columns={"order_date": "second_order_date"})

    customers = (
        orders.groupby("customer_id", as_index=False)
        .agg(
            last_order_date=("order_date", "max"),
            total_orders=("invoice", "size"),
            gross_revenue=("total_revenue", "sum"),
            total_items=("total_items", "sum"),
            country=("country", lambda values: values.mode().iloc[0]),
        )
        .merge(first, on="customer_id", how="left")
        .merge(second, on="customer_id", how="left")
    )
    customers["cohort_month"] = (
        customers["first_order_date"].dt.to_period("M").astype(str)
    )
    customers["time_to_second_order_days"] = (
        customers["second_order_date"] - customers["first_order_date"]
    ).dt.days
    customers["made_second_purchase"] = customers["second_order_date"].notna().astype(int)
    return customers


def add_lifetime_return_features(
    customers: pd.DataFrame, cancellations: pd.DataFrame
) -> pd.DataFrame:
    """Add lifetime cancellation and net-revenue fields."""
    returns = cancellations.groupby("customer_id", as_index=False).agg(
        refund_value=("revenue", "sum"),
        return_lines=("invoice", "size"),
    )
    result = customers.merge(returns, on="customer_id", how="left")
    result["refund_value"] = pd.to_numeric(
        result["refund_value"], errors="coerce"
    ).fillna(0.0)
    result["return_lines"] = pd.to_numeric(
        result["return_lines"], errors="coerce"
    ).fillna(0).astype(int)
    result["had_return"] = (result["return_lines"] > 0).astype(int)
    result["net_revenue"] = result["gross_revenue"] + result["refund_value"]
    return result


def _quartile_score(series: pd.Series, higher_is_better: bool) -> pd.Series:
    """Score 1-4 by empirical percentile while keeping tied values together."""
    percentile = series.rank(method="max", pct=True)
    score = np.ceil(percentile * 4).clip(1, 4).astype(int)
    return score if higher_is_better else 5 - score


def _rfm_tier(row: pd.Series) -> str:
    """Return an exhaustive, mutually exclusive RFM tier."""
    r, f, m = int(row["r_score"]), int(row["f_score"]), int(row["m_score"])
    if r >= 3:
        if f >= 3 and m >= 3:
            return "Champions"
        if f == 1:
            return "New"
        return "Loyal"
    if f >= 3 or m >= 3:
        return "At Risk"
    return "Lost"


def build_customer_snapshot(
    orders: pd.DataFrame,
    cancellations: pd.DataFrame,
    observation_end: pd.Timestamp = OBSERVATION_END,
    outcome_end: pd.Timestamp = DATASET_END,
) -> pd.DataFrame:
    """Build pre-cutoff RFM features and a strictly post-cutoff outcome."""
    observation_end = pd.Timestamp(observation_end).normalize()
    outcome_end = pd.Timestamp(outcome_end).normalize()
    observed = orders[orders["order_date"] <= observation_end].copy()
    future = orders[
        (orders["order_date"] > observation_end)
        & (orders["order_date"] <= outcome_end)
    ]

    snapshot = observed.groupby("customer_id", as_index=False).agg(
        first_order_date=("order_date", "min"),
        last_order_date=("order_date", "max"),
        frequency=("invoice", "size"),
        monetary=("total_revenue", "sum"),
    )
    snapshot["recency_days"] = (
        observation_end - snapshot["last_order_date"]
    ).dt.days

    snapshot["r_score"] = _quartile_score(snapshot["recency_days"], False)
    snapshot["m_score"] = _quartile_score(snapshot["monetary"], True)
    snapshot["f_score"] = pd.cut(
        snapshot["frequency"],
        bins=[0, 1, 3, 7, np.inf],
        labels=[1, 2, 3, 4],
        right=True,
    ).astype(int)
    snapshot["rfm_tier"] = snapshot.apply(_rfm_tier, axis=1)

    retained_ids = set(future["customer_id"].unique())
    snapshot["retained_in_outcome"] = snapshot["customer_id"].isin(retained_ids).astype(int)
    snapshot["churned_in_outcome"] = 1 - snapshot["retained_in_outcome"]

    observed_returns = cancellations[
        cancellations["invoice_date"].dt.normalize() <= observation_end
    ]
    return_summary = observed_returns.groupby("customer_id", as_index=False).agg(
        refund_value=("revenue", "sum"),
        return_lines=("invoice", "size"),
    )
    snapshot = snapshot.merge(return_summary, on="customer_id", how="left")
    snapshot["refund_value"] = pd.to_numeric(
        snapshot["refund_value"], errors="coerce"
    ).fillna(0.0)
    snapshot["return_lines"] = pd.to_numeric(
        snapshot["return_lines"], errors="coerce"
    ).fillna(0).astype(int)
    snapshot["had_return"] = (snapshot["return_lines"] > 0).astype(int)
    snapshot["net_monetary"] = snapshot["monetary"] + snapshot["refund_value"]
    snapshot["observation_end"] = observation_end.strftime("%Y-%m-%d")
    snapshot["outcome_end"] = outcome_end.strftime("%Y-%m-%d")
    snapshot["outcome_days"] = (outcome_end - observation_end).days
    return snapshot


def load() -> None:
    print("Reading source CSV...")
    raw = load_raw()
    print(f"  {len(raw):,} source rows")

    raw, duplicate_count = drop_exact_duplicates(raw)
    print(f"  {duplicate_count:,} exact duplicate rows removed")

    identified, anonymous = split_anonymous(raw)
    cancellations = extract_cancellations(identified)
    transactions = clean_transactions(identified)
    anonymous_transactions = clean_transactions(anonymous)

    orders = build_orders(transactions)
    customers = add_lifetime_return_features(
        build_customers(orders), cancellations
    )
    snapshot = build_customer_snapshot(orders, cancellations)
    sensitivity = pd.concat(
        [
            build_customer_snapshot(
                orders,
                cancellations,
                observation_end=DATASET_END - pd.Timedelta(days=window_days),
                outcome_end=DATASET_END,
            )
            for window_days in SENSITIVITY_WINDOWS
        ],
        ignore_index=True,
    )

    print(
        f"  {len(transactions):,} identified sales lines | "
        f"{len(anonymous_transactions):,} anonymous sales lines"
    )
    print(f"  {len(orders):,} orders | {len(customers):,} customers")
    print(
        f"  snapshot: {len(snapshot):,} eligible customers as of "
        f"{OBSERVATION_END.date()}"
    )

    con = sqlite3.connect(DB_PATH)
    transactions.to_sql("transactions", con, if_exists="replace", index=False)
    anonymous_transactions.to_sql(
        "anonymous_tx", con, if_exists="replace", index=False
    )
    cancellations.to_sql("cancellations", con, if_exists="replace", index=False)
    orders.to_sql("orders", con, if_exists="replace", index=False)
    customers.to_sql("customers", con, if_exists="replace", index=False)
    snapshot.to_sql("customer_snapshot", con, if_exists="replace", index=False)
    sensitivity.to_sql(
        "customer_snapshot_sensitivity", con, if_exists="replace", index=False
    )
    con.close()

    print(f"\nLoaded 7 tables into {DB_PATH}")
    print(snapshot["rfm_tier"].value_counts().to_string())
    print(f"Future 90-day churn: {snapshot['churned_in_outcome'].mean():.1%}")


if __name__ == "__main__":
    load()
