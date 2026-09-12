from __future__ import annotations

import io
import json
import logging
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT_DIR = Path(__file__).resolve().parents[1]
SRC_DIR = ROOT_DIR / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from spritter.providers.omv import provider as omv_provider
from spritter.types import FuelStationRequest

LOGGER = logging.getLogger(__name__)


class _FakeJsonResponse(io.StringIO):
    def __init__(self, payload: dict[str, object], status: int = 200, reason: str = "OK"):
        super().__init__(json.dumps(payload))
        self.status = status
        self.reason = reason

    def __enter__(self) -> _FakeJsonResponse:
        return self

    def __exit__(self, exc_type, exc, tb) -> bool:
        self.close()
        return False


def _build_fake_urlopen(prices_payload: list[dict]):
    """Build mock urlopen response for the single details endpoint call."""
    details_payload = {
        "siteDetails": {
            "sid": "AT.4518.8",
            "brand_id": "OMV",
        },
        "prices": prices_payload,
    }
    responses = [
        _FakeJsonResponse(details_payload),
    ]

    def _fake_urlopen(_request, timeout=5):
        if not responses:
            raise AssertionError("Unexpected extra urlopen call")
        return responses.pop(0)

    return _fake_urlopen


class TestOmvProvider(unittest.TestCase):
    def test_fetch_fuel_prices_parses_json_prices_with_mocked_api(self):
        mock_prices = [
            {"name": "DIESEL", "price": "2.184", "currency": "EUR", "date": "2026-09-12 22:40"},
            {"name": "SUPER 95", "price": "1.942", "currency": "EUR", "date": "2026-09-12 22:40"},
        ]
        expected_prices = {"DIESEL": 2.184, "SUPER 95": 1.942}

        request = FuelStationRequest(provider="omv", station_id="Thalgau-AT.4518.8")

        with patch(
            "spritter.providers.omv.lib.api.urlopen",
            side_effect=_build_fake_urlopen(mock_prices),
        ) as mocked_urlopen:
            result = omv_provider.fetch_fuel_prices(request)
            output_map = result.to_price_map()

        LOGGER.info("Expected prices: %s", expected_prices)
        LOGGER.info("Actual prices: %s", output_map)

        # Assert prices exist and are not empty
        self.assertTrue(output_map, "Expected prices map to not be empty")
        self.assertIn("DIESEL", output_map)
        self.assertIn("SUPER 95", output_map)
        self.assertEqual(output_map, expected_prices)

        # Now only 1 request is performed directly to details.php
        self.assertEqual(mocked_urlopen.call_count, 1)

    def test_fetch_fuel_prices_live_api(self):
        request = FuelStationRequest(provider="omv", station_id="Salzburg-AT.4546.8")

        result = omv_provider.fetch_fuel_prices(request)
        output_map = result.to_price_map()

        self.assertIsInstance(output_map, dict)
        # Assert prices exist and each fuel type has a valid positive price
        self.assertTrue(output_map, "No fuel prices returned from station")
        self.assertGreater(len(output_map), 0)
        for fuel_type, price in output_map.items():
            self.assertIsInstance(price, (int, float))
            self.assertGreater(price, 0, f"Price for {fuel_type} must be greater than 0")


if __name__ == "__main__":
    unittest.main()