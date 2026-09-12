"""Integration tests for OMV provider using parameterized test configurations."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
SRC_DIR = ROOT_DIR / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from spritter import get_fuel_prices
from spritter.types import FuelStationRequest, FuelPriceResult


# Test configurations for OMV provider
OMV_STATIONS = [
    {"name": "OMV Thalgau", "station_id": "Thalgau-AT.4520.8"},
    {"name": "OMV Vogelweider", "station_id": "Salzburg-AT.4546.8"},
    {"name": "OMV Nonntal", "station_id": "Salzburg-AT.4605.8"},
]


class TestOmvProvider(unittest.TestCase):
    """Parameterized integration tests for OMV provider stations."""

    def test_fetch_omv_fuel_prices(self):
        """Test fetching fuel prices for OMV stations."""
        for config in OMV_STATIONS:
            with self.subTest(station=config["name"]):
                request = FuelStationRequest(provider="OMV", station_id=config["station_id"])
                result = get_fuel_prices(request)

                self.assertIsInstance(result, FuelPriceResult)
                self.assertEqual(result.provider, "OMV")
                self.assertEqual(result.station_id, config["station_id"])
                self.assertIsNotNone(result.quotes, f"No quotes returned for {config['name']}")


if __name__ == "__main__":
    unittest.main()
