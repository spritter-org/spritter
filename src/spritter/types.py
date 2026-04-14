from __future__ import annotations

from dataclasses import dataclass


FuelPriceValue = float | str
FuelPriceMap = dict[str, FuelPriceValue]


@dataclass(frozen=True, slots=True)
class FuelStationRequest:
    provider: str
    station_id: str
    user_agent: str | None = None
    keys: tuple[str, ...] | None = None

    @property
    def normalized_provider(self) -> str:
        return self.provider.strip().lower()

    @property
    def normalized_station_id(self) -> str:
        return self.station_id.strip()

    @property
    def normalized_user_agent(self) -> str | None:
        if self.user_agent is None:
            return None
        normalized = self.user_agent.strip()
        return normalized or None

    @property
    def normalized_keys(self) -> tuple[str, ...] | None:
        if self.keys is None:
            return None
        normalized = tuple(key.strip().lower() for key in self.keys if key.strip())
        return normalized if normalized else None


@dataclass(frozen=True, slots=True)
class FuelPriceQuote:
    fuel_type: str
    price: FuelPriceValue


@dataclass(frozen=True, slots=True)
class FuelPriceResult:
    provider: str
    station_id: str
    quotes: tuple[FuelPriceQuote, ...]

    @classmethod
    def from_price_map(
        cls,
        *,
        provider: str,
        station_id: str,
        prices: FuelPriceMap,
    ) -> FuelPriceResult:
        quotes = tuple(
            FuelPriceQuote(fuel_type=fuel_type, price=price)
            for fuel_type, price in prices.items()
        )
        return cls(
            provider=provider,
            station_id=station_id,
            quotes=quotes,
        )

    def to_price_map(self, keys: tuple[str, ...] | None = None) -> FuelPriceMap:
        price_map = {quote.fuel_type: quote.price for quote in self.quotes}

        if keys is None:
            return price_map

        keys_lower = {key.lower() for key in keys}

        return {
            fuel_type: price
            for fuel_type, price in price_map.items()
            if fuel_type.lower() in keys_lower
        }
