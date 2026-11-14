import io
import unittest
import pandas as pd
from vendor_import import import_npcs, merge_catalog, parse_addon_csv

class FakeResponse:
    def __init__(self, value): self.value = value
    def raise_for_status(self): pass
    def json(self): return self.value

class FakeSession:
    def __init__(self): self.calls = []
    def get(self, url, params=None, **kwargs):
        self.calls.append((url, params))
        if url.endswith("/sells"):
            if params.get("cursor"):
                return FakeResponse({"data": [{"item": {"id": 2, "name": "Recipe B"}, "cost": {"money": 400}}], "has_more": False})
            return FakeResponse({"data": [
                {"item": {"id": 1, "name": "Recipe A"}, "cost": {"money": 200}},
                {"item": {"id": 3, "name": "Honor"}, "cost": {"money": 100, "honor": 2}}],
                "has_more": True, "next_cursor": "next"})
        return FakeResponse({"name": "Marchand", "english_name": "Vendor", "zones": [{"name": "Stormwind"}]})

class ImportTests(unittest.TestCase):
    def test_pagination_and_copper_only(self):
        session = FakeSession()
        frame = import_npcs([3090], session=session, pause=0)
        self.assertEqual(frame.item_id.tolist(), ["1", "2"])
        self.assertEqual(frame.vendor_buy_copper.tolist(), [200, 400])
        self.assertFalse(frame.verified.any())
        self.assertEqual(len(session.calls), 3)

    def test_preserve_verified(self):
        existing = pd.DataFrame([{"item_id": "1", "item_name": "Corrected", "vendor_name": "Vendor", "vendor_buy_copper": 150, "verified": True}])
        imported = pd.DataFrame([{"item_id": "1", "item_name": "Classic", "vendor_name": "Vendor", "vendor_buy_copper": 200, "verified": False}])
        merged = merge_catalog(existing, imported)
        self.assertEqual(len(merged), 1)
        self.assertEqual(merged.iloc[0]["vendor_buy_copper"], 150)

    def test_addon_csv_unverified(self):
        csv = io.StringIO("item_id,item_name,vendor_name,vendor_buy_copper\n1,Recipe,Vendor,100\n")
        frame = parse_addon_csv(csv)
        self.assertFalse(frame.iloc[0]["verified"])

if __name__ == "__main__":
    unittest.main()
