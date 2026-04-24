# Spritter library

Simple fuel price getter library.

## Providers

### BP

Browse for petrol stations on [bp.com Tankstellenfinder](https://www.bp.com/de_at/austria/home/produkte-und-services/bp-in-ihrer-naehe.html). Get the station ID from the network log in the browser developer tools. You're looking for a GET request to a route like `GET https://bpretaillocator.geoapp.me/api/v2/locations/AT-420?locale=de_AT&format=json`, where `420` would be the station ID.

### JET

Browse for petrol stations on [jet-austria.at](https://www.jet-austria.at). Get the station ID from the network log in the browser developer tools. You're looking for a GET request to a route like `https://www.jet-austria.at/api/stations/id/aabbcc`, where `aabbcc` would be the station ID.

### OMV, AVANTI, HOFER

Browse for petrol stations on the lists down below. Get the station ID (e.g. `Thalgau-AT.4518.8`) from the browser address bar after you click the link.

List of petrol stations:

- [OMV](https://www.omv.at/de/mobilitaet/kraftstoffe/tankstelle-finden?id=oesterreich)
- [Avanti](https://www.avanti.at/de/tankstellensuche?id=oesterreich)
- [Hofer (diskonttanken.at)](https://www.diskonttanken.at/de/tankstellensuche?id=oesterreich)

> Note: Prices are currently extracted via OCR, which generally works quite well. Very basic fuzzy logic is in place to extract tokens somewhat robustly in case something goes wrong during OCR.

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
