from __future__ import annotations

from data_collection.collectors.boundary_collector import BoundaryCollector
from data_collection.clients.nominatim_client import NominatimClient
from data_collection.config import CURATED_NEIGHBOURHOODS
from data_collection.transformers.normalization import safe_float, slugify, stable_id


class NeighbourhoodCollector:
    def __init__(self):
        self.client = NominatimClient()
        self.boundary_collector = BoundaryCollector()

    def collect(self) -> list[dict]:
        rows = {row["slug"]: row for row in self.boundary_collector.collect()}
        north_york_id = stable_id("neighbourhood", "North York")
        rows.setdefault(
            "north-york",
            {
                "id": north_york_id,
                "slug": "north-york",
                "name": "North York",
                "display_name": "North York, Toronto, Ontario, Canada",
                "city": "Toronto",
                "province": "Ontario",
                "country": "Canada",
                "latitude": 43.7615,
                "longitude": -79.4111,
                "boundary_geojson": None,
                "source": "curated_seed",
                "payload": {"source": "curated_seed"},
            }
        )

        for name in CURATED_NEIGHBOURHOODS:
            query = f"{name}, North York, Toronto, Ontario, Canada"
            geocoded = self.client.geocode(query)
            slug = slugify(name)
            rows[slug] = {
                    "id": stable_id("neighbourhood", name),
                    "slug": slug,
                    "name": name,
                    "display_name": geocoded.get("display_name", query) if geocoded else query,
                    "city": "Toronto",
                    "province": "Ontario",
                    "country": "Canada",
                    "latitude": safe_float(geocoded.get("lat")) if geocoded else None,
                    "longitude": safe_float(geocoded.get("lon")) if geocoded else None,
                    "boundary_geojson": rows.get(slug, {}).get("boundary_geojson"),
                    "source": rows.get(slug, {}).get("source", "nominatim"),
                    "payload": rows.get(slug, {}).get("payload", geocoded or {"query": query}),
                }
        return list(rows.values())
