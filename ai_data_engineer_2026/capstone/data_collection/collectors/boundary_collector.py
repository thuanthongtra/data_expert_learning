from __future__ import annotations

import os

from data_collection.clients.open_data_client import OpenDataClient
from data_collection.config import CURATED_NEIGHBOURHOODS
from data_collection.transformers.normalization import safe_float, slugify, stable_id


class BoundaryCollector:
    def __init__(self):
        self.client = OpenDataClient()

    def collect(self) -> list[dict]:
        url = (os.environ.get("TORONTO_NEIGHBOURHOOD_BOUNDARIES_SOURCE_URL") or "").strip()
        if not url:
            return []
        try:
            rows = self.client.fetch_rows(url)
        except Exception:
            return []
        records = []
        for row in rows:
            name = self._name(row)
            if not name:
                continue
            slug = slugify(name)
            if name not in CURATED_NEIGHBOURHOODS and slug != "north-york":
                continue
            latitude, longitude = self._lat_lon(row)
            records.append(
                {
                    "id": stable_id("neighbourhood", name),
                    "slug": slug,
                    "name": name,
                    "display_name": row.get("AREA_NAME") or row.get("name") or name,
                    "city": "Toronto",
                    "province": "Ontario",
                    "country": "Canada",
                    "latitude": latitude,
                    "longitude": longitude,
                    "boundary_geojson": row.get("geometry"),
                    "source": "toronto_open_data_boundaries",
                    "payload": row,
                }
            )
        return records

    def _name(self, row: dict) -> str | None:
        for key in ("AREA_NAME", "area_name", "name", "Neighbourhood", "neighbourhood"):
            value = row.get(key)
            if value:
                return str(value).strip()
        return None

    def _lat_lon(self, row: dict) -> tuple[float | None, float | None]:
        geometry = row.get("geometry") or {}
        coords = geometry.get("coordinates") if isinstance(geometry, dict) else None
        if isinstance(coords, list):
            points = self._flatten_points(coords)
            if points:
                xs = [p[0] for p in points]
                ys = [p[1] for p in points]
                return sum(ys) / len(ys), sum(xs) / len(xs)
        return safe_float(row.get("latitude")), safe_float(row.get("longitude"))

    def _flatten_points(self, coords: list) -> list[tuple[float, float]]:
        points: list[tuple[float, float]] = []
        if len(coords) >= 2 and all(isinstance(item, (int, float)) for item in coords[:2]):
            points.append((float(coords[0]), float(coords[1])))
            return points
        for item in coords:
            if isinstance(item, list):
                points.extend(self._flatten_points(item))
        return points
