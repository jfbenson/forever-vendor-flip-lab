import unittest
from engine import listing_forecast

class ListingForecastTests(unittest.TestCase):
    def test_zero_demand(self):
        self.assertEqual(listing_forecast(0, 0, 7, 0.65, 10)["list_units"], 0)

    def test_high_demand_can_list_more(self):
        low = listing_forecast(1, 10, 7, 0.65, 20)
        high = listing_forecast(100, 10, 7, 0.65, 20)
        self.assertGreaterEqual(high["list_units"], low["list_units"])
        self.assertEqual(high["list_units"], 20)

    def test_competition_reduces_listing_quantity(self):
        no_comp = listing_forecast(8, 0, 7, 0.65, 20)
        many_comp = listing_forecast(8, 100, 7, 0.65, 20)
        self.assertGreaterEqual(no_comp["list_units"], many_comp["list_units"])

    def test_expected_sales_bounds(self):
        result = listing_forecast(20, 5, 7, 0.65, 10)
        self.assertLessEqual(result["expected_sold"], result["list_units"])
        self.assertGreaterEqual(result["expected_unsold"], 0)

if __name__ == "__main__":
    unittest.main()
