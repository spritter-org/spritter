import json
import logging
import ssl
from urllib.request import Request, urlopen
from . import config
from ....types import FuelPriceMap

logger = logging.getLogger(__name__)


def _parse_fuel_prices(payload: dict, station_id: str) -> FuelPriceMap:
    raw_prices = payload.get("fuelPrices")

    if not isinstance(raw_prices, dict):
        logger.warning(
            f"JET response for station '{station_id}' does not contain fuelPrices"
        )
        return {}

    prices: FuelPriceMap = {}
    for label, raw_price in raw_prices.items():
        if not isinstance(label, str):
            continue

        if not isinstance(raw_price, (int, float)):
            continue

        prices[label] = float(raw_price)

    return prices


def fetch_fuel_prices(station_id : str) -> FuelPriceMap:
    if not station_id:
        raise RuntimeError("JET station id must not be empty")

    request_url = config.JET_STATION_URL.format(station_id=station_id)

    logger.debug("Requesting JET station data: %s", request_url)

    headers = {**config.JET_HEADERS}
    http_request = Request(request_url, headers=headers, method="GET")
    try:
        with urlopen(http_request, timeout=6, context=ssl._create_unverified_context()) as response:
            payload = json.load(response)
    except Exception as exc:
        raise RuntimeError(
            f"Failed to fetch JET station data for '{station_id}': {exc}"
        ) from exc

    return _parse_fuel_prices(payload=payload, station_id=station_id)
