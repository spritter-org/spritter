"""Integration tests for BP provider using parameterized test configurations."""

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


# Test configurations for BP provider
BP_STATIONS = [
    {"name": "BP Glasenbach", "station_id": "AT-7074", "min_prices": 0},
]


class TestBpProvider(unittest.TestCase):
    """Parameterized integration tests for BP provider stations."""

    def test_fetch_bp_fuel_prices(self):
        """Test fetching fuel prices for BP stations."""
        for config in BP_STATIONS:
            with self.subTest(station=config["name"]):
                request = FuelStationRequest(provider="BP", station_id=config["station_id"])
                result = get_fuel_prices(request)

                self.assertIsInstance(result, FuelPriceResult)
                self.assertEqual(result.provider, "BP")
                self.assertEqual(result.station_id, config["station_id"])
                self.assertIsNotNone(result.quotes, f"No quotes returned for {config['name']}")
                self.assertGreaterEqual(
                    len(result.quotes),
                    config.get("min_prices", 1),
                    f"Expected at least {config.get('min_prices', 1)} prices for {config['name']}, got {len(result.quotes)}",
                )


if __name__ == "__main__":
    unittest.main()