import tempfile
import unittest
from pathlib import Path
import zipfile
from kaydee_import import import_forever_addon, read_forever_text

SAMPLE = '''
ns.DATA_ITEMS = {
[728]={"Recipe: Westfall Stew",1,9,5,0,200,1,nil,nil,nil,nil,nil,{340},{340}},
[159]={"Refreshing Spring Water",1,0,5,1,25,5,nil,nil,nil,nil,nil,{151,2140},nil,nil,{[2140]=23}},
}
ns.DATA_NPCS = {
[340]={"Kendor Kabonka","Recipes","A",1453,77.33,52.59,"Old Town"},
[151]={"Brog Hamfist","General","A",1429,43.87,65.89},
[2140]={"Vendor","General","A",1429,43.87,65.89},
}
'''

class KaydeeImportTests(unittest.TestCase):
    def test_forever_data(self):
        df = read_forever_text(SAMPLE)
        self.assertEqual(len(df), 3)
        recipe = df[df.item_id == "728"].iloc[0]
        self.assertEqual(recipe.vendor_buy_copper, 200)
        self.assertEqual(recipe.vendor_name, "Kendor Kabonka")
        self.assertTrue(recipe.limited_stock)
        self.assertFalse(recipe.verified)
        self.assertEqual(df[df.npc_id == 2140].iloc[0].vendor_buy_copper, 23)

    def test_zip_import(self):
        with tempfile.TemporaryDirectory() as tmp:
            archive = Path(tmp) / "addon.zip"
            with zipfile.ZipFile(archive, "w") as z:
                z.writestr("KaydeesVID/Data_Forever.lua", SAMPLE)
            self.assertEqual(len(import_forever_addon(archive)), 3)

if __name__ == "__main__":
    unittest.main()
