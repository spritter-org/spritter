from __future__ import annotations

import base64
import json
import logging
import re
from . import config, types
from difflib import SequenceMatcher
from io import BytesIO
from urllib.parse import urlencode
from urllib.request import Request, urlopen

import pytesseract
from PIL import Image

from ....types import FuelPriceMap, FuelPriceResult, FuelStationRequest

logger = logging.getLogger(__name__)


def fetch_fuel_prices(request: FuelStationRequest, brand: str) -> FuelPriceResult:
    station_id = request.normalized_station_id
    if not station_id:
        raise RuntimeError(f"{brand} station id must not be empty")

    if not brand or not brand.strip():
        raise RuntimeError("Brand must not be empty")

    normalized_brand = brand.strip()
    user_agent = request.normalized_user_agent or config.OMV_DEFAULT_USER_AGENT

    station_info = get_station_info(
        station_id=station_id,
        brand=normalized_brand,
        user_agent=user_agent,
    )

    details_payload = _fetch_station_details(
        station_id=station_id,
        brand=normalized_brand,
        station_info=station_info,
        user_agent=user_agent,
    )

    prices = _extract_ocr_price_map(
        details_payload=details_payload,
        brand=normalized_brand,
        station_id=station_id,
    )
    return FuelPriceResult.from_price_map(
        provider=request.provider,
        station_id=station_id,
        prices=prices,
    )


def get_station_info(station_id: str, brand: str, user_agent: str) -> types.OmvStationInfo:
    query = {**config.OMV_DEFAULT_QUERY,
             "BRAND": brand, "STATIONID": station_id}
    request_url = f"{config.OMV_BASE_URL}?{urlencode(query)}"
    logger.debug(
        "Requesting station info: brand=%s station_id=%s url=%s",
        brand,
        station_id,
        request_url,
    )
    headers = _build_request_headers(brand=brand, user_agent=user_agent)
    request = Request(request_url, headers=headers, method="POST")

    try:
        with urlopen(request, timeout=5) as response:
            logger.debug("status=%d reason=%s",
                         response.status, response.reason)
            result = json.load(response)
            logger.debug("Station info: %s", result)
            return _parse_station_info(result)
    except Exception as exc:
        raise RuntimeError(
            f"Failed to fetch station info for {brand} station '{station_id}': {exc}"
        ) from exc


def _parse_station_info(payload: object) -> types.OmvStationInfo:
    if not isinstance(payload, dict):
        raise RuntimeError("Station info response is not an object")

    ts = str(payload.get("ts", "")).strip()
    hash_value = str(payload.get("hash", "")).strip()
    site_number_key = (
        str(
            payload.get("confVariables", {})
            .get("conf_STATIONDETAILS", {})
            .get("site_number_key", "")
        )
        .strip()
    )

    if not ts or not hash_value or not site_number_key:
        raise RuntimeError("Station info payload missing required fields")

    return types.OmvStationInfo(
        ts=ts,
        hash_value=hash_value,
        site_number_key=site_number_key,
    )


def _build_request_headers(brand: str, user_agent: str) -> dict[str, str]:
    normalized_brand = brand.strip().upper()
    brand_headers = config.OMV_BRAND_SITE_HEADERS.get(normalized_brand, {})
    headers = {
        **config.OMV_DEFAULT_BROWSER_HEADERS,
        **brand_headers,
        "User-Agent": user_agent,
    }
    return headers


def _fetch_station_details(
    station_id: str,
    brand: str,
    station_info: types.OmvStationInfo,
    user_agent: str,
) -> dict[str, object]:
    query = {
        **config.OMV_DEFAULT_DETAILS_QUERY,
        "BRAND": brand,
        "ID": station_info.site_number_key,
        "HASH": station_info.hash_value,
        "TS": station_info.ts,
    }

    request_body = urlencode(query).encode("utf-8")
    logger.debug("Requesting station details: query=%s", query)
    headers = _build_request_headers(brand=brand, user_agent=user_agent)
    headers = {
        **headers,
        "Content-Type": "application/x-www-form-urlencoded",
    }
    request = Request(config.OMV_DETAILS_URL, data=request_body,
                      headers=headers, method="POST")

    try:
        with urlopen(request, timeout=5) as response:
            logger.debug("status=%d reason=%s",
                         response.status, response.reason)
            result = json.load(response)
            logger.debug("Station details: %s", result)
            if not isinstance(result, dict):
                raise RuntimeError("Station details response is not an object")
            return result
    except Exception as exc:
        raise RuntimeError(
            f"Failed to fetch station details for {brand} station '{station_id}': {exc}"
        ) from exc


def _extract_ocr_price_map(
    details_payload: dict,
    brand: str,
    station_id: str,
) -> FuelPriceMap:
    price_url = details_payload.get("priceUrl")
    logger.debug(
        "Extracting OCR payload station_id=%s details_keys=%s",
        station_id,
        sorted(details_payload.keys()) if isinstance(
            details_payload, dict) else type(details_payload).__name__,
    )
    if not isinstance(price_url, str) or not price_url.strip():
        logger.warning(
            "%s details response for '%s' does not contain priceUrl",
            brand,
            station_id,
        )
        return {}

    image_bytes = _decode_price_image(price_url=price_url)
    logger.debug(
        "Decoded price image bytes station_id=%s bytes=%d",
        station_id,
        len(image_bytes),
    )
    image = _load_image_with_white_background(image_bytes=image_bytes)
    logger.debug(
        "Prepared OCR image station_id=%s size=%s",
        station_id,
        getattr(image, "size", None),
    )

    text = pytesseract.image_to_string(image)
    normalized = " ".join(text.split())
    logger.info(
        "OCR completed station_id=%s characters=%d",
        station_id,
        len(normalized),
    )
    logger.debug("OCR raw output station_id=%s text=%s",
                 station_id, normalized)

    prices = _extract_prices_from_ocr_text(normalized)
    if not prices:
        raise RuntimeError(
            f"Failed to extract fuel prices from OCR output for {brand} station '{station_id}': {normalized}"
        )

    logger.debug("OCR parsed prices station_id=%s prices=%s",
                 station_id, prices)
    return prices


def _extract_prices_from_ocr_text(text: str) -> FuelPriceMap:
    prices: FuelPriceMap = {}

    for match in config.OMV_OCR_PRICE_PATTERN.finditer(text):
        label = _extract_label_before_price(text, match.start())
        if not label:
            continue

        key = _match_ocr_label(label)
        if not key:
            continue

        prices[key] = float(match.group("price").replace(",", "."))

    return prices


def _extract_label_before_price(text: str, price_start: int) -> str | None:
    tokens = text[:price_start].split()
    if not tokens:
        return None

    while tokens and _is_currency_token(tokens[-1]):
        tokens.pop()

    if not tokens:
        return None

    best_suffix: str | None = None
    best_score = 0.0

    max_tokens = min(config.OMV_OCR_LABEL_MAX_TOKENS, len(tokens))
    for size in range(1, max_tokens + 1):
        candidate_tokens = tokens[-size:]
        candidate = " ".join(candidate_tokens).strip()
        if not candidate:
            continue

        score = _score_ocr_label(candidate)
        if score > best_score:
            best_score = score
            best_suffix = candidate

    if best_suffix is None or best_score < config.OMV_OCR_LABEL_MATCH_THRESHOLD:
        return None

    return best_suffix


def _is_label_token(token: str) -> bool:
    normalized = token.strip().strip(",;:|()").strip()
    if not normalized:
        return False

    lowered = normalized.lower()
    if lowered in config.OMV_OCR_STOP_TOKENS:
        return False

    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", normalized):
        return False
    if re.fullmatch(r"\d{1,2}:\d{2}(?::\d{2})?", normalized):
        return False
    if re.fullmatch(r"\d+[.,]\d{2,3}", normalized):
        return False

    if any(ch.isalpha() for ch in normalized):
        return True

    return normalized.isdigit() and len(normalized) <= 3


def _is_currency_token(token: str) -> bool:
    normalized = token.strip().strip(",;:|()")
    if not normalized:
        return False
    return normalized.casefold() in config.OMV_OCR_CURRENCY_TOKENS


def _match_ocr_label(label: str) -> str | None:
    best_key: str | None = None
    best_score = 0.0
    label_normalized = label.casefold()

    for key, aliases in config.OMV_OCR_FUEL_TERMS.items():
        for alias in aliases:
            score = SequenceMatcher(
                None, label_normalized, alias.casefold()).ratio()
            if score > best_score:
                best_score = score
                best_key = key

    if best_key is None or best_score < config.OMV_OCR_LABEL_MATCH_THRESHOLD:
        return None

    return best_key


def _score_ocr_label(label: str) -> float:
    label_normalized = label.casefold()
    best_score = 0.0

    for aliases in config.OMV_OCR_FUEL_TERMS.values():
        for alias in aliases:
            score = SequenceMatcher(
                None, label_normalized, alias.casefold()).ratio()
            if score > best_score:
                best_score = score

    return best_score


def _decode_price_image(price_url: str) -> bytes:
    encoded_image = price_url.strip()
    if "," in encoded_image:
        encoded_image = encoded_image.split(",", 1)[1]

    try:
        return base64.b64decode(encoded_image, validate=True)
    except Exception as exc:
        raise RuntimeError(
            f"Failed to decode priceUrl image: {exc}"
        ) from exc


def _load_image_with_white_background(image_bytes: bytes):
    try:
        image = Image.open(BytesIO(image_bytes)).convert("RGBA")
    except Exception as exc:
        raise RuntimeError(
            f"Failed to read priceUrl image: {exc}"
        ) from exc

    white_background = Image.new(
        "RGBA", image.size, (255, 255, 255, 255))
    composited = Image.alpha_composite(white_background, image)
    return composited.convert("RGB")
