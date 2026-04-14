from __future__ import annotations

import logging
from .lib import api

from ...types import FuelPriceResult, FuelStationRequest

logger = logging.getLogger(__name__)

def fetch_fuel_prices(station_request: FuelStationRequest) -> FuelPriceResult:
    station_id = station_request.normalized_station_id

    return FuelPriceResult.from_price_map(
        provider=station_request.provider,
        station_id=station_id,
        prices=api.fetch_fuel_prices(station_id=station_id),
    )
