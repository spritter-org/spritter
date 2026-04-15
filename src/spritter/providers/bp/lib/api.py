from __future__ import annotations

import json
import logging
import re
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from ....types import FuelPriceMap, FuelPriceResult, FuelStationRequest
from . import config

logger = logging.getLogger(__name__)

_PRICE_PATTERN = re.compile(r"\d+[.,]\d+")


def fetch_fuel_prices(request: FuelStationRequest) -> FuelPriceResult:
    station_id = request.normalized_station_id
    if not station_id:
        raise RuntimeError("BP station id must not be empty")

    payload = _fetch_station_payload(station_id=station_id)
    prices = _extract_prices(payload=payload, station_id=station_id)

    return FuelPriceResult.from_price_map(
        provider=request.provider,
        station_id=station_id,
        prices=prices,
    )


def _fetch_station_payload(station_id: str) -> dict[str, object]:
    query = {
        "locale": config.BP_DEFAULT_LOCALE,
        "format": "json",
    }
    request_url = f"{config.BP_BASE_URL.format(station_id=station_id)}?{urlencode(query)}"
    logger.debug("Requesting BP station data: %s", request_url)

    headers = {
        **config.BP_HEADERS,
        "Referer": f"https://bpretaillocator.geoapp.me/?locale={config.BP_DEFAULT_LOCALE}",
    }
    request = Request(request_url, headers=headers, method="GET")

    try:
        with urlopen(request, timeout=6) as response:
            payload = json.load(response)
    except Exception as exc:
        raise RuntimeError(
            f"Failed to fetch BP station data for '{station_id}': {exc}"
        ) from exc

    if not isinstance(payload, dict):
        raise RuntimeError("BP response is not an object")

    return payload


def _extract_prices(payload: dict[str, object], station_id: str) -> FuelPriceMap:
    fuel_pricing = payload.get("fuel_pricing")
    if not isinstance(fuel_pricing, dict):
        logger.warning("BP response for station '%s' does not contain fuel_pricing", station_id)
        return {}

    raw_prices = fuel_pricing.get("prices")
    if not isinstance(raw_prices, dict):
        logger.warning("BP response for station '%s' does not contain fuel_pricing.prices", station_id)
        return {}

    prices: FuelPriceMap = {}
    for label, raw_price in raw_prices.items():
        if not isinstance(label, str):
            continue

        price = _parse_price_value(raw_price)
        if price is None:
            logger.debug(
                "Skipping unparsable BP price for station '%s': %r=%r",
                station_id,
                label,
                raw_price,
            )
            continue

        prices[label] = price

    return prices


def _parse_price_value(value: object) -> float | None:
    if isinstance(value, (int, float)):
        return float(value)

    if not isinstance(value, str):
        return None

    text = value.strip()
    if not text:
        return None

    match = _PRICE_PATTERN.search(text.replace(" ", ""))
    if match is None:
        match = _PRICE_PATTERN.search(text)
    if match is None:
        return None

    normalized = match.group(0).replace(",", ".")
    try:
        return float(normalized)
    except ValueError:
        return None
