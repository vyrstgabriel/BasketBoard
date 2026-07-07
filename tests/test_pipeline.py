"""Regression tests for Basketboard's analytical data contracts."""

from pathlib import Path
import unittest

import pandas as pd

from src.load_db import (
    RAW_CSV,
    _rfm_tier,
    build_customer_snapshot,
    build_orders,
    clean_transactions,
    drop_exact_duplicates,
    load_raw,
    split_anonymous,
)


class PipelineUnitTests(unittest.TestCase):
    def test_exact_duplicates_are_removed(self):
        row = {
            "invoice": "1",
            "stock_code": "A",
            "description": "item",
            "quantity": 2,
            "invoice_date": pd.Timestamp("2011-01-01 10:00"),
            "price": 3.0,
            "customer_id": "10",
            "country": "United Kingdom",
        }
        cleaned, removed = drop_exact_duplicates(pd.DataFrame([row, row]))
        self.assertEqual(removed, 1)
        self.assertEqual(len(cleaned), 1)

    def test_invoice_lines_with_nearby_timestamps_form_one_order(self):
        tx = pd.DataFrame(
            {
                "invoice": ["1", "1"],
                "stock_code": ["A", "B"],
                "description": ["first", "second"],
                "quantity": [1, 2],
                "invoice_date": pd.to_datetime(
                    ["2011-01-01 10:00", "2011-01-01 10:01"]
                ),
                "price": [2.0, 3.0],
                "customer_id": ["10", "10"],
                "country": ["United Kingdom", "United Kingdom"],
                "revenue": [2.0, 6.0],
            }
        )
        orders = build_orders(tx)
        self.assertEqual(len(orders), 1)
        self.assertEqual(orders.loc[0, "total_revenue"], 8.0)
        self.assertEqual(orders.loc[0, "line_items"], 2)

    def test_rfm_tiers_are_exhaustive_and_use_monetary_score(self):
        champion = pd.Series({"r_score": 4, "f_score": 3, "m_score": 3})
        loyal = pd.Series({"r_score": 4, "f_score": 3, "m_score": 2})
        at_risk = pd.Series({"r_score": 2, "f_score": 1, "m_score": 4})
        lost = pd.Series({"r_score": 2, "f_score": 1, "m_score": 1})
        self.assertEqual(_rfm_tier(champion), "Champions")
        self.assertEqual(_rfm_tier(loyal), "Loyal")
        self.assertEqual(_rfm_tier(at_risk), "At Risk")
        self.assertEqual(_rfm_tier(lost), "Lost")

    def test_snapshot_excludes_future_only_customers_and_separates_outcome(self):
        orders = pd.DataFrame(
            {
                "customer_id": ["A", "A", "B", "C"],
                "invoice": ["1", "2", "3", "4"],
                "order_date": pd.to_datetime(
                    ["2011-08-01", "2011-10-01", "2011-08-15", "2011-10-02"]
                ),
                "total_revenue": [10.0, 20.0, 30.0, 40.0],
            }
        )
        cancellations = pd.DataFrame(
            columns=["customer_id", "invoice", "invoice_date", "revenue"]
        )
        cancellations["invoice_date"] = pd.to_datetime(cancellations["invoice_date"])

        snapshot = build_customer_snapshot(
            orders,
            cancellations,
            observation_end=pd.Timestamp("2011-09-01"),
            outcome_end=pd.Timestamp("2011-11-30"),
        ).set_index("customer_id")

        self.assertEqual(set(snapshot.index), {"A", "B"})
        self.assertEqual(snapshot.loc["A", "frequency"], 1)
        self.assertEqual(snapshot.loc["A", "retained_in_outcome"], 1)
        self.assertEqual(snapshot.loc["B", "retained_in_outcome"], 0)


@unittest.skipUnless(Path(RAW_CSV).exists(), "raw UCI CSV is not available")
class RawDataIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.raw = load_raw()
        cls.deduplicated, cls.duplicates_removed = drop_exact_duplicates(cls.raw)
        identified, _ = split_anonymous(cls.deduplicated)
        cls.transactions = clean_transactions(identified)
        cls.orders = build_orders(cls.transactions)

    def test_expected_source_contract(self):
        self.assertEqual(len(self.raw), 1_067_371)
        self.assertEqual(self.duplicates_removed, 34_335)
        self.assertEqual(len(self.transactions), 779_425)
        self.assertEqual(len(self.orders), 36_969)

    def test_clean_sales_are_positive_and_revenue_reconciles(self):
        self.assertTrue((self.transactions["quantity"] > 0).all())
        self.assertTrue((self.transactions["price"] > 0).all())
        expected = self.transactions["quantity"] * self.transactions["price"]
        pd.testing.assert_series_equal(
            self.transactions["revenue"], expected, check_names=False
        )

    def test_order_grain_is_unique(self):
        self.assertFalse(self.orders["invoice"].duplicated().any())


if __name__ == "__main__":
    unittest.main()
