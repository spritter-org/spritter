from __future__ import annotations

from typing import Callable
from .providers import avanti, jet, omv
from .types import FuelPriceResult, FuelStationRequest

_PROVIDER_FETCHERS: dict[str, Callable[[FuelStationRequest], FuelPriceResult]] = {
    "jet": jet.fetch_fuel_prices,
    "omv": omv.fetch_fuel_prices,
    "avanti": avanti.fetch_fuel_prices,
}


def _resolve_provider(provider: str) -> Callable[[FuelStationRequest], FuelPriceResult]:
    normalized = provider.strip().lower()
    fetch = _PROVIDER_FETCHERS.get(normalized)

    if fetch is None:
        supported = ", ".join(sorted(_PROVIDER_FETCHERS))
        raise ValueError(
            f"Unsupported provider '{provider}'. Supported providers: {supported}"
        )

    return fetch


def get_fuel_prices(request: FuelStationRequest) -> FuelPriceResult:
    """Return fuel prices for the given provider and station ID."""
    fetch = _resolve_provider(request.normalized_provider)
    result = fetch(request)

    return result
