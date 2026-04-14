JET_STATION_URL = "https://www.jet-austria.at/api/stations/id/{station_id}"

JET_HEADERS: dict[str, str] = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:148.0) Gecko/20100101 Firefox/148.0",
    "Accept": "application/json",
    "Connection": "keep-alive",
    "Sec-Fetch-Dest": "empty",
    "Sec-Fetch-Mode": "cors",
    "Sec-Fetch-Site": "same-origin",
    "Priority": "u=4",
    "Pragma": "no-cache",
    "Cache-Control": "no-cache",
}
