import unittest
import pandas as pd
from vendor_import import merge_catalog
from faction_filter import filter_vendors

class FactionRecoveryTests(unittest.TestCase):
    def test_reimport_restores_missing_faction_preserves_edits(self):
        old = pd.DataFrame([{"item_id":"85","item_name":"Vest","vendor_name":"Vendor",
            "vendor_buy_copper":50,"verified":True}])
        incoming = pd.DataFrame([{"item_id":"85","item_name":"Vest","vendor_name":"Vendor",
            "vendor_buy_copper":62,"verified":False,"faction":"A","npc_id":42}])
        merged = merge_catalog(old, incoming)
        self.assertEqual(len(merged), 1)
        self.assertEqual(merged.iloc[0].vendor_buy_copper, 50)
        self.assertTrue(merged.iloc[0].verified)
        self.assertEqual(merged.iloc[0].faction, "A")
        self.assertEqual(len(filter_vendors(merged, "Alliance")), 1)
        self.assertEqual(len(filter_vendors(merged, "Horde")), 0)

if __name__ == "__main__":
    unittest.main()
