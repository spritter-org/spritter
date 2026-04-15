BP_BASE_URL = "https://bpretaillocator.geoapp.me/api/v2/locations/{station_id}"
BP_DEFAULT_LOCALE = "de_AT"

BP_HEADERS: dict[str, str] = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:148.0) Gecko/20100101 Firefox/148.0",
    "Accept": "*/*",
    "Accept-Language": "en,de-AT;q=0.9,de-DE;q=0.8",
    "Connection": "keep-alive",
    "Sec-Fetch-Dest": "empty",
    "Sec-Fetch-Mode": "cors",
    "Sec-Fetch-Site": "same-origin",
    "Priority": "u=0",
    "Pragma": "no-cache",
    "Cache-Control": "no-cache",
    "DNT": "1",
}
