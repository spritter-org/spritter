from __future__ import annotations

import base64
import io
import json
import logging
import sys
from pathlib import Path
from unittest.mock import patch
import unittest

ROOT_DIR = Path(__file__).resolve().parents[1]
SRC_DIR = ROOT_DIR / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from spritter.providers.omv import provider as omv_provider
from spritter.types import FuelStationRequest


FIXTURES_DIR = ROOT_DIR / "tests" / "fixtures" / "omv"
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


def _build_fake_urlopen(price_url: str):
    station_payload = {
        "ts": "1234",
        "hash": "abc123",
        "confVariables": {
            "conf_STATIONDETAILS": {
                "site_number_key": "mock-site-id",
            }
        },
    }
    details_payload = {"priceUrl": price_url}
    responses = [
        _FakeJsonResponse(station_payload),
        _FakeJsonResponse(details_payload),
    ]

    def _fake_urlopen(_request, timeout=5):
        if not responses:
            raise AssertionError("Unexpected extra urlopen call")
        return responses.pop(0)

    return _fake_urlopen


def _parse_expected_prices(ocr_text: str) -> dict[str, float]:
    expected: dict[str, float] = {}

    for raw_line in ocr_text.splitlines():
        line = " ".join(raw_line.split())
        if not line:
            continue

        tokens = line.split()
        if len(tokens) < 2:
            continue

        has_currency_suffix = tokens[-1].casefold() in {"eur", "€"}
        price_token = tokens[-2] if has_currency_suffix else tokens[-1]
        label_tokens = tokens[:-2] if has_currency_suffix else tokens[:-1]
        if not label_tokens:
            continue

        expected[" ".join(label_tokens)] = float(price_token.replace(",", "."))

    return expected


def _fixture_base_names() -> list[str]:
    txt_names = {path.stem for path in FIXTURES_DIR.glob("*.txt")}
    png_names = {path.stem for path in FIXTURES_DIR.glob("*.png")}
    return sorted(txt_names & png_names)


class TestOmvProvider(unittest.TestCase):
    def test_fetch_fuel_prices_parses_all_ocr_rows_with_mocked_api(self):
        fixture_names = _fixture_base_names()
        self.assertGreater(len(fixture_names), 0, "No OMV fixtures found")

        for fixture_name in fixture_names:
            with self.subTest(fixture=fixture_name):
                image_bytes = (FIXTURES_DIR / f"{fixture_name}.png").read_bytes()
                ocr_text = (FIXTURES_DIR / f"{fixture_name}.txt").read_text(encoding="utf-8")
                expected_prices = _parse_expected_prices(ocr_text)

                price_url = f"data:image/png;base64,{base64.b64encode(image_bytes).decode('ascii')}"
                request = FuelStationRequest(provider="omv", station_id="Thalgau-AT.4518.8")

                with patch(
                    "spritter.providers.omv.lib.api.urlopen",
                    side_effect=_build_fake_urlopen(price_url),
                ) as mocked_urlopen:
                    result = omv_provider.fetch_fuel_prices(request)
                    output_map = result.to_price_map()

                LOGGER.info("Fixture %s expected prices: %s", fixture_name, expected_prices)
                LOGGER.info("Fixture %s actual prices: %s", fixture_name, output_map)

                self.assertEqual(output_map, expected_prices)
                self.assertEqual(mocked_urlopen.call_count, 2)

    def test_fetch_fuel_prices_live_api(self):
        request = FuelStationRequest(provider="omv", station_id="Salzburg-AT.4546.8")

        result = omv_provider.fetch_fuel_prices(request)
        output_map = result.to_price_map()

        self.assertIsInstance(output_map, dict)
        self.assertGreater(len(output_map), 0)


if __name__ == "__main__":
    unittest.main()