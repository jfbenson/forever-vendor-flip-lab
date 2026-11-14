import unittest
from ahledger import decode

class AHL1Tests(unittest.TestCase):
    def test_valid(self):
        raw = b"AHL1|forever/normal/alliance/us|1794641639|2\n25:1000:1000:1:833:692:100:1000:24\n35:400:400:8:667:515:100:2464:40\n"
        frame = decode(raw)
        self.assertEqual(len(frame), 2)
        self.assertEqual(frame.loc[0, "item_id"], 25)
        self.assertEqual(frame.loc[0, "field_8"], 24)
        self.assertEqual(frame.attrs["format"], "AHL1")
        self.assertEqual(frame.attrs["timestamp"], 1794641639)

    def test_wrong_count(self):
        with self.assertRaisesRegex(ValueError, "count mismatch"):
            decode(b"AHL1|realm|123|2\n25:1:2:3:4:5:6:7:8\n")

    def test_malformed_record(self):
        with self.assertRaisesRegex(ValueError, "Malformed AHL1 record"):
            decode(b"AHL1|realm|123|1\n25:1:2\n")

    def test_duplicate_id(self):
        with self.assertRaisesRegex(ValueError, "Duplicate AHL1"):
            decode(b"AHL1|realm|123|2\n25:1:2:3:4:5:6:7:8\n25:1:2:3:4:5:6:7:8\n")

if __name__ == "__main__":
    unittest.main()
