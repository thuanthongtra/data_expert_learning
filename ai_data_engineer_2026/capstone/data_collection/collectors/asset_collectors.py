from __future__ import annotations

from data_collection.clients.overpass_client import OverpassClient
from data_collection.transformers.normalization import safe_float, stable_id


class AssetCollector:
    def __init__(self, radius_meters: int = 1500):
        self.client = OverpassClient()
        self.radius_meters = radius_meters

    def collect_schools(self, neighbourhoods: list[dict]) -> list[dict]:
        return self._collect(
            neighbourhoods,
            '["amenity"~"school|college|university|kindergarten"]',
            "schools",
            self._school_record,
        )

    def collect_transit_stations(self, neighbourhoods: list[dict]) -> list[dict]:
        records = []
        for neighbourhood in neighbourhoods:
            lat = neighbourhood.get("latitude")
            lon = neighbourhood.get("longitude")
            if lat is None or lon is None:
                continue
            query = f"""
[out:json][timeout:60];
(
  node["public_transport"~"station|platform|stop_position"](around:{self.radius_meters},{lat},{lon});
  way["public_transport"~"station|platform|stop_position"](around:{self.radius_meters},{lat},{lon});
  relation["public_transport"~"station|platform|stop_position"](around:{self.radius_meters},{lat},{lon});
  node["railway"~"station|subway_entrance"](around:{self.radius_meters},{lat},{lon});
  way["railway"~"station|subway_entrance"](around:{self.radius_meters},{lat},{lon});
  relation["railway"~"station|subway_entrance"](around:{self.radius_meters},{lat},{lon});
);
out center tags;
"""
            try:
                elements = self.client.query(query)
            except Exception:
                continue
            for element in elements:
                record = self._transit_record(neighbourhood, element, "transit_stations")
                if record:
                    records.append(record)
        deduped: dict[str, dict] = {}
        for record in records:
            deduped[record["id"]] = record
        return list(deduped.values())

    def collect_parks(self, neighbourhoods: list[dict]) -> list[dict]:
        return self._collect(
            neighbourhoods,
            '["leisure"="park"]',
            "parks",
            self._park_record,
        )

    def collect_amenities(self, neighbourhoods: list[dict]) -> list[dict]:
        return self._collect(
            neighbourhoods,
            '["amenity"~"library|hospital|clinic|pharmacy|community_centre|community_center|bank|cafe|restaurant"]',
            "amenities",
            self._amenity_record,
        )

    def _collect(self, neighbourhoods: list[dict], tag_filter: str, kind: str, record_builder) -> list[dict]:
        records = []
        for neighbourhood in neighbourhoods:
            lat = neighbourhood.get("latitude")
            lon = neighbourhood.get("longitude")
            if lat is None or lon is None:
                continue
            query = self._query(lat, lon, tag_filter)
            try:
                elements = self.client.query(query)
            except Exception:
                continue
            for element in elements:
                record = record_builder(neighbourhood, element, kind)
                if record:
                    records.append(record)
        deduped: dict[str, dict] = {}
        for record in records:
            deduped[record["id"]] = record
        return list(deduped.values())

    def _query(self, lat: float, lon: float, tag_filter: str) -> str:
        return f"""
[out:json][timeout:60];
(
  node{tag_filter}(around:{self.radius_meters},{lat},{lon});
  way{tag_filter}(around:{self.radius_meters},{lat},{lon});
  relation{tag_filter}(around:{self.radius_meters},{lat},{lon});
);
out center tags;
"""

    def _school_record(self, neighbourhood: dict, element: dict, kind: str) -> dict | None:
        tags = element.get("tags") or {}
        name = tags.get("name")
        if not name:
            return None
        return {
            "id": stable_id(kind, element.get("type"), element.get("id")),
            "neighbourhood_slug": neighbourhood["slug"],
            "name": name,
            "school_type": tags.get("amenity"),
            "operator": tags.get("operator"),
            "grades": tags.get("grades"),
            "address": self._address(tags),
            "latitude": self._lat(element),
            "longitude": self._lon(element),
            "source": "openstreetmap",
            "payload": element,
        }

    def _transit_record(self, neighbourhood: dict, element: dict, kind: str) -> dict | None:
        tags = element.get("tags") or {}
        name = tags.get("name") or tags.get("official_name") or f"Transit stop {element.get('id')}"
        return {
            "id": stable_id(kind, element.get("type"), element.get("id")),
            "neighbourhood_slug": neighbourhood["slug"],
            "name": name,
            "mode": tags.get("railway") or tags.get("public_transport") or tags.get("route"),
            "line_name": tags.get("line") or tags.get("network"),
            "address": self._address(tags),
            "latitude": self._lat(element),
            "longitude": self._lon(element),
            "source": "openstreetmap",
            "payload": element,
        }

    def _park_record(self, neighbourhood: dict, element: dict, kind: str) -> dict | None:
        tags = element.get("tags") or {}
        name = tags.get("name") or f"Park {element.get('id')}"
        return {
            "id": stable_id(kind, element.get("type"), element.get("id")),
            "neighbourhood_slug": neighbourhood["slug"],
            "name": name,
            "park_type": tags.get("leisure") or tags.get("landuse"),
            "address": self._address(tags),
            "latitude": self._lat(element),
            "longitude": self._lon(element),
            "source": "openstreetmap",
            "payload": element,
        }

    def _amenity_record(self, neighbourhood: dict, element: dict, kind: str) -> dict | None:
        tags = element.get("tags") or {}
        name = tags.get("name") or f"Amenity {element.get('id')}"
        return {
            "id": stable_id(kind, element.get("type"), element.get("id")),
            "neighbourhood_slug": neighbourhood["slug"],
            "name": name,
            "amenity_type": tags.get("amenity") or tags.get("shop") or tags.get("tourism"),
            "address": self._address(tags),
            "latitude": self._lat(element),
            "longitude": self._lon(element),
            "source": "openstreetmap",
            "payload": element,
        }

    def _address(self, tags: dict) -> str | None:
        parts = [
            tags.get("addr:housenumber"),
            tags.get("addr:street"),
            tags.get("addr:city"),
        ]
        value = " ".join(part for part in parts if part)
        return value or None

    def _lat(self, element: dict) -> float | None:
        return safe_float(element.get("lat") or (element.get("center") or {}).get("lat"))

    def _lon(self, element: dict) -> float | None:
        return safe_float(element.get("lon") or (element.get("center") or {}).get("lon"))
