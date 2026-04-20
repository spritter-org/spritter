from __future__ import annotations

import json
import logging
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from . import config, types
from .ocr import OcrService, OcrCorrector
from ....types import FuelPriceResult, FuelStationRequest

logger = logging.getLogger(__name__)


def fetch_fuel_prices(request: FuelStationRequest, brand: str = "OMV") -> FuelPriceResult:
    station_id = request.normalized_station_id
    if not station_id:
        raise RuntimeError(f"{brand} station id must not be empty")

    normalized_brand = brand.strip()
    user_agent = request.normalized_user_agent or config.OMV_DEFAULT_USER_AGENT

    station_info = _get_station_info(station_id, normalized_brand, user_agent)
    details = _fetch_station_details(station_id, normalized_brand, station_info, user_agent)
    
    price_url = details.get("priceUrl")
    prices = {}
    
    if price_url:
        ocr_service = OcrService(corrector=OcrCorrector())
        try:
            prices = ocr_service.extract_from_base64_url(price_url)
        except Exception as e:
            raise RuntimeError(
                f"Failed to extract fuel prices from OCR output for {normalized_brand} station '{station_id}': {e}"
            ) from e
    else:
        logger.warning("%s details response for '%s' does not contain priceUrl", normalized_brand, station_id)

    return FuelPriceResult.from_price_map(
        provider=request.provider,
        station_id=station_id,
        prices=prices,
    )


def _get_station_info(station_id: str, brand: str, user_agent: str) -> types.OmvStationInfo:
    query = {**config.OMV_DEFAULT_QUERY, "BRAND": brand, "STATIONID": station_id}
    url = f"{config.OMV_BASE_URL}?{urlencode(query)}"
    headers = _build_request_headers(brand, user_agent)
    
    try:
        with urlopen(Request(url, headers=headers, method="POST"), timeout=5) as response:
            payload = json.load(response)
            
            ts = str(payload.get("ts", "")).strip()
            hash_val = str(payload.get("hash", "")).strip()
            site_key = str(payload.get("confVariables", {}).get("conf_STATIONDETAILS", {}).get("site_number_key", "")).strip()
            
            if not all([ts, hash_val, site_key]):
                raise RuntimeError("Station info payload missing required fields")
                
            return types.OmvStationInfo(ts=ts, hash_value=hash_val, site_number_key=site_key)
            
    except Exception as exc:
        raise RuntimeError(f"Failed to fetch station info for {brand} station '{station_id}': {exc}") from exc


def _fetch_station_details(station_id: str, brand: str, info: types.OmvStationInfo, user_agent: str) -> dict:
    query = {
        **config.OMV_DEFAULT_DETAILS_QUERY,
        "BRAND": brand,
        "ID": info.site_number_key,
        "HASH": info.hash_value,
        "TS": info.ts,
    }
    
    headers = {
        **_build_request_headers(brand, user_agent),
        "Content-Type": "application/x-www-form-urlencoded",
    }
    
    try:
        with urlopen(Request(config.OMV_DETAILS_URL, data=urlencode(query).encode("utf-8"), headers=headers, method="POST"), timeout=5) as response:
            return json.load(response)
    except Exception as exc:
        raise RuntimeError(f"Failed to fetch station details for {brand} station '{station_id}': {exc}") from exc


def _build_request_headers(brand: str, user_agent: str) -> dict[str, str]:
    brand_headers = config.OMV_BRAND_SITE_HEADERS.get(brand.upper(), {})
    return {
        **config.OMV_DEFAULT_BROWSER_HEADERS,
        **brand_headers,
        "User-Agent": user_agent,
    }