# Spritter library

Simple fuel price getter library.

## Providers

- JET
- OMV (+ Avanti)

## Install

```bash
pip install -e .
```

## Usage

```python
import spritter

request = spritter.FuelStationRequest(
    provider="jet",
    station_id="12345",
)

result = spritter.get_fuel_prices(request)
print(result)
```
