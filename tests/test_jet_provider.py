"""Integration tests for JET provider using parameterized test configurations."""

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


# Test configurations for JET provider
JET_STATIONS = [
    {"name": "Jet Alpenstraße", "station_id": "27a8add058"},
    {"name": "Jet Thalgau", "station_id": "2640f98f48"},
]


class TestJetProvider(unittest.TestCase):
    """Parameterized integration tests for JET provider stations."""

    def test_fetch_jet_fuel_prices(self):
        """Test fetching fuel prices for JET stations."""
        for config in JET_STATIONS:
            with self.subTest(station=config["name"]):
                request = FuelStationRequest(provider="JET", station_id=config["station_id"])
                result = get_fuel_prices(request)

                self.assertIsInstance(result, FuelPriceResult)
                self.assertEqual(result.provider, "JET")
                self.assertEqual(result.station_id, config["station_id"])
                self.assertIsNotNone(result.quotes, f"No quotes returned for {config['name']}")


if __name__ == "__main__":
    unittest.main()
