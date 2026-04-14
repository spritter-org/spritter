from __future__ import annotations

from . import lib
from ...types import FuelPriceResult, FuelStationRequest


def fetch_fuel_prices(request: FuelStationRequest) -> FuelPriceResult:
    return lib.fetch_fuel_prices(request=request, brand="OMV")
