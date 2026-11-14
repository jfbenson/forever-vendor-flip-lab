import unittest
import pandas as pd
from stock_filter import stock_category, filter_vendor_stock, stock_counts

class StockFilterTests(unittest.TestCase):
    def test_kaydee_flags_and_missing_metadata(self):
        frame = pd.DataFrame({"limited_stock": [False, True, None, "false", "true"],
                              "stock": [None, None, None, None, None]})
        self.assertEqual(stock_category(frame).tolist(),
                         ["unlimited", "limited", "unknown", "unlimited", "limited"])
        self.assertEqual(len(filter_vendor_stock(frame, "Unlimited only")), 2)

    def test_finite_stock_overrides_unlimited(self):
        frame = pd.DataFrame({"limited_stock": [False, False, None],
                              "stock": [5, None, 2]})
        self.assertEqual(stock_category(frame).tolist(),
                         ["limited", "unlimited", "limited"])

    def test_missing_columns_are_unknown(self):
        frame = pd.DataFrame({"item_id": ["1", "2"]})
        self.assertEqual(stock_counts(frame)["unknown"], 2)
        self.assertEqual(len(filter_vendor_stock(frame, "Unlimited only")), 0)

    def test_all_preserves_rows(self):
        frame = pd.DataFrame({"limited_stock": [True, False, None]})
        self.assertEqual(len(filter_vendor_stock(frame, "All stock types")), 3)

if __name__ == "__main__":
    unittest.main()
