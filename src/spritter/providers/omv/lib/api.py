from __future__ import annotations

import json
import logging
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from . import config
from ....types import FuelPriceResult, FuelStationRequest

logger = logging.getLogger(__name__)


def _strip_station_id(station_id: str | None, warn: bool = True) -> str:
    """Strip any prefix up to the first dash and optionally warn if deprecated format is used."""
    if not station_id:
        return ""

    if "-" in station_id:
        clean_station_id = station_id.split("-", 1)[1].strip()
        if warn:
            logger.warning(
                "Station ID '%s' is deprecated, '%s' shall be used instead",
                station_id,
                clean_station_id,
            )
        return clean_station_id

    return station_id.strip()


def fetch_fuel_prices(request: FuelStationRequest, brand: str = "OMV") -> FuelPriceResult:
    """Fetch and return current fuel prices for the requested station."""
    station_id = _strip_station_id(request.normalized_station_id)
    if not station_id:
        raise RuntimeError(f"{brand} station id must not be empty")

    normalized_brand = brand.strip()
    user_agent = request.normalized_user_agent or getattr(config, "OMV_DEFAULT_USER_AGENT", "Mozilla/5.0")

    details = _fetch_station_details(station_id, normalized_brand, user_agent)

    prices: dict[str, float] = {}

    if "prices" in details and isinstance(details["prices"], list):
        for entry in details["prices"]:
            try:
                name = entry["name"]
                price_val = float(entry["price"])
                prices[name] = price_val
            except (KeyError, ValueError, TypeError):
                logger.warning("Could not parse price entry for station '%s': %s", station_id, entry)

        logger.debug("Parsed OMV fuel prices for station '%s' (%s): %s", station_id, normalized_brand, prices)
    else:
        logger.warning("%s details response for '%s' does not contain a prices array", normalized_brand, station_id)

    return FuelPriceResult.from_price_map(
        provider=request.provider,
        station_id=station_id,
        prices=prices,
    )


def _fetch_station_details(station_id: str, brand: str, user_agent: str) -> dict:
    """Directly fetch station details and fuel prices in a single request."""
    default_details = getattr(config, "OMV_DEFAULT_DETAILS_QUERY", {})
    query = {
        "BRAND": brand,
        "CTRISO": "AUT",
        "LNG": default_details.get("LNG", "DE"),
        "MODE": default_details.get("MODE", "NEXTDOOR"),
        "ID": station_id,
        **default_details,
    }
    # Ensure ID, CTRISO, and BRAND are fixed
    query["BRAND"] = brand
    query["ID"] = station_id
    query["CTRISO"] = "AUT"

    headers = _build_request_headers(brand, user_agent)
    details_url = getattr(config, "OMV_DETAILS_URL", "https://app.wigeogis.com/kunden/omv/data/details.php")

    logger.info("Requesting OMV station details URL for station '%s' (%s): %s", station_id, brand, details_url)
    logger.debug("OMV station details payload: %s", query)

    try:
        req = Request(
            details_url,
            data=urlencode(query).encode("utf-8"),
            headers=headers,
            method="POST",
        )
        with urlopen(req, timeout=5) as response:
            payload = json.load(response)
            logger.debug("Parsed OMV station details payload for station '%s' (%s): %s", station_id, brand, payload)
            return payload
    except Exception as exc:
        raise RuntimeError(f"Failed to fetch station details for {brand} station '{station_id}': {exc}") from exc


def _build_request_headers(brand: str, user_agent: str) -> dict[str, str]:
    brand_headers = getattr(config, "OMV_BRAND_SITE_HEADERS", {}).get(brand.upper(), {})
    default_headers = getattr(config, "OMV_DEFAULT_BROWSER_HEADERS", {})
    return {
        **default_headers,
        **brand_headers,
        "User-Agent": user_agent,
        "Accept": "application/json, text/plain, */*",
        "Content-Type": "application/x-www-form-urlencoded",
    }