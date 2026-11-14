import tempfile
import unittest
from datetime import datetime, timezone, timedelta
from pathlib import Path
from local_store import load_market

STAMP = 1794641639
RAW = (f"AHL1|forever/normal/alliance/us|{STAMP}|1\n"
       "25:1000:800:4:900:950:700:1500:24\n").encode()
NOW = datetime.fromtimestamp(STAMP, tz=timezone.utc) + timedelta(hours=1)

class MarketCacheTests(unittest.TestCase):
    def test_fetch_then_cache(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "market.raw"
            calls = []
            def fetcher(url):
                calls.append(url)
                return RAW
            frame, status = load_market(path=path, fetcher=fetcher, now=NOW)
            self.assertEqual(status["source"], "AHledger (saved locally)")
            self.assertEqual(frame.iloc[0]["daily_sales"], 2.4)
            self.assertEqual(frame.iloc[0]["competing_units"], 4)
            self.assertTrue(path.exists())
            _, status = load_market(path=path, fetcher=fetcher, now=NOW)
            self.assertEqual(status["source"], "local cache")
            self.assertEqual(len(calls), 1)

    def test_offline_fallback(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "market.raw"
            path.write_bytes(RAW)
            def fail(url):
                raise ConnectionError("offline")
            _, status = load_market(path=path, fetcher=fail,
                                    now=NOW + timedelta(days=2))
            self.assertEqual(status["source"], "offline fallback")
            self.assertIn("offline", status["warning"])

    def test_no_cache_offline(self):
        with tempfile.TemporaryDirectory() as tmp:
            def fail(url):
                raise ConnectionError("offline")
            with self.assertRaises(RuntimeError):
                load_market(path=Path(tmp) / "missing.raw", fetcher=fail, now=NOW)

if __name__ == "__main__":
    unittest.main()
