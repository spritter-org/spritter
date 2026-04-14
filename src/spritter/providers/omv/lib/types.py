from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class OmvStationInfo:
    ts: str
    hash_value: str
    site_number_key: str
