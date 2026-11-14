import unittest
import pandas as pd
from faction_filter import filter_vendors, faction_counts

class FactionFilterTests(unittest.TestCase):
    def setUp(self):
        self.vendors = pd.DataFrame([
            {"item_id":"1","faction":"A"},
            {"item_id":"2","faction":"H"},
            {"item_id":"3","faction":"AH"},
            {"item_id":"4","faction":None},
        ])

    def test_alliance_includes_shared(self):
        self.assertEqual(filter_vendors(self.vendors, "Alliance").item_id.tolist(), ["1", "3"])

    def test_horde_includes_shared(self):
        self.assertEqual(filter_vendors(self.vendors, "Horde").item_id.tolist(), ["2", "3"])

    def test_all_includes_unknown(self):
        self.assertEqual(len(filter_vendors(self.vendors, "All")), 4)
        self.assertEqual(faction_counts(self.vendors)["unknown"], 1)

    def test_missing_faction_column(self):
        old = self.vendors.drop(columns=["faction"])
        self.assertTrue(filter_vendors(old, "Alliance").empty)
        self.assertEqual(len(filter_vendors(old, "All")), 4)

if __name__ == "__main__":
    unittest.main()
