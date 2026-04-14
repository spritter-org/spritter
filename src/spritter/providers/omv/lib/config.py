import re

OMV_BASE_URL = "https://app.wigeogis.com/kunden/omv/data/getconfig.php"
OMV_DETAILS_URL = "https://app.wigeogis.com/kunden/omv/data/details.php"

OMV_DEFAULT_QUERY: dict[str, str] = {
    "CTRISO": "AUT",
    "LNG": "DE",
    "FILTERS": "",
}

OMV_DEFAULT_DETAILS_QUERY: dict[str, str] = {
    "LNG": "EN",
    "CTRISO": "AUT",
    "VEHICLE": "CAR",
    "MODE": "NEXTDOOR",
    "DISTANCE": "0",
}

OMV_DEFAULT_BROWSER_HEADERS: dict[str, str] = {
    "Host": "app.wigeogis.com",
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:148.0) Gecko/20100101 Firefox/148.0",
    "Accept": "*/*",
    "Accept-Language": "en,de-AT;q=0.9,de-DE;q=0.8",
    "Connection": "keep-alive",
    "Sec-Fetch-Dest": "empty",
    "Sec-Fetch-Mode": "cors",
    "Sec-Fetch-Site": "cross-site",
    "Priority": "u=4",
    "Pragma": "no-cache",
    "Cache-Control": "no-cache",
}

OMV_DEFAULT_USER_AGENT = OMV_DEFAULT_BROWSER_HEADERS["User-Agent"]

OMV_BRAND_SITE_HEADERS: dict[str, dict[str, str]] = {
    "AVANTI": {
        "Origin": "https://www.avanti.at",
        "Referer": "https://www.avanti.at/",
    },
    "OMV": {
        "Origin": "https://www.omv.at",
        "Referer": "https://www.omv.at/",
    },
}

OMV_OCR_FUEL_TERMS: dict[str, tuple[str, ...]] = {
    "Diesel": ("DIESEL",),
    "Diesel Plus": ("Diesel Plus", "DIESEL PLUS"),
    "Super 95": ("SUPER 95", "SUPER95"),
}
OMV_OCR_PRICE_PATTERN = re.compile(
    r"(?P<price>\d+[.,]\d{2,3})(?:\s*(?:EUR|€))?\b",
    re.IGNORECASE,
)
OMV_OCR_STOP_TOKENS = {"date", "time", "date/time", "ocr"}
OMV_OCR_CURRENCY_TOKENS = {"eur", "€"}
OMV_OCR_LABEL_MAX_TOKENS = 4
OMV_OCR_LABEL_MATCH_THRESHOLD = 0.72
