from __future__ import annotations

import os
import logging

from data_collection.clients.open_data_client import OpenDataClient
from data_collection.transformers.normalization import safe_float, slugify, stable_id


logger = logging.getLogger("real-estate-civic-collectors")


class CivicCollectors:
    def __init__(self):
        self.client = OpenDataClient()

    def collect_crime_events(self, neighbourhoods: list[dict]) -> list[dict]:
        rows = self._fetch_if_configured("TORONTO_CRIME_SOURCE_URL")
        records = []
        for row in rows:
            lat = self._extract_lat(row)
            lon = self._extract_lon(row)
            area_slug = self._match_area_slug(neighbourhoods, row, lat, lon)
            if area_slug is None:
                continue
            event_type = self._value(row, "event_type", "category", "offence", "type") or "unknown"
            occurred_at = self._value(row, "occurred_at", "reported_date", "date", "occurrence_date")
            records.append(
                {
                    "id": stable_id("crime", event_type, occurred_at, lat, lon, self._value(row, "id", "OBJECTID")),
                    "area_slug": area_slug,
                    "event_type": event_type,
                    "occurred_at": occurred_at,
                    "latitude": lat,
                    "longitude": lon,
                    "source": "configured_open_data",
                    "payload": row,
                }
            )
        return self._dedupe(records)

    def collect_development_applications(self, neighbourhoods: list[dict]) -> list[dict]:
        rows = self._fetch_if_configured("TORONTO_DEVELOPMENT_SOURCE_URL")
        records = []
        for row in rows:
            lat = self._extract_lat(row)
            lon = self._extract_lon(row)
            area_slug = self._match_area_slug(neighbourhoods, row, lat, lon)
            if area_slug is None:
                continue
            title = self._value(row, "title", "application_type", "description", "name") or "Development Application"
            application_id = self._value(row, "application_number", "file_no", "id", "OBJECTID")
            records.append(
                {
                    "id": stable_id("development", application_id, title),
                    "area_slug": area_slug,
                    "title": title,
                    "status": self._value(row, "status", "application_status"),
                    "address": self._value(row, "address", "site_address", "location"),
                    "application_type": self._value(row, "application_type", "type"),
                    "submitted_at": self._value(row, "submitted_at", "received_date", "date_submitted"),
                    "latitude": lat,
                    "longitude": lon,
                    "source": "configured_open_data",
                    "payload": row,
                }
            )
        return self._dedupe(records)

    def collect_zoning_areas(self, neighbourhoods: list[dict]) -> list[dict]:
        rows = self._fetch_if_configured("TORONTO_ZONING_SOURCE_URL")
        records = []
        for row in rows:
            lat = self._extract_lat(row)
            lon = self._extract_lon(row)
            area_slug = self._match_area_slug(neighbourhoods, row, lat, lon)
            if area_slug is None:
                continue
            zone_code = self._value(row, "zone", "zone_code", "zoning", "category") or "unknown"
            records.append(
                {
                    "id": stable_id("zoning", area_slug, zone_code, self._value(row, "id", "OBJECTID")),
                    "area_slug": area_slug,
                    "zone_code": zone_code,
                    "zone_label": self._value(row, "zone_label", "description", "label"),
                    "address": self._value(row, "address", "location"),
                    "latitude": lat,
                    "longitude": lon,
                    "source": "configured_open_data",
                    "payload": row,
                }
            )
        return self._dedupe(records)

    def collect_demographic_snapshots(self, neighbourhoods: list[dict]) -> list[dict]:
        rows = self._fetch_if_configured("TORONTO_DEMOGRAPHICS_SOURCE_URL")
        records = []
        for row in rows:
            area_slug = self._match_area_slug(neighbourhoods, row, self._extract_lat(row), self._extract_lon(row))
            if area_slug is None:
                continue
            snapshot_date = self._value(row, "snapshot_date", "date", "year") or "2026-01-01"
            for metric_name in ("population", "median_income", "households", "renters_pct"):
                metric_value = safe_float(self._value(row, metric_name, metric_name.upper()))
                if metric_value is None:
                    continue
                records.append(
                    {
                        "id": stable_id("demographic", area_slug, metric_name, snapshot_date),
                        "area_slug": area_slug,
                        "snapshot_date": snapshot_date,
                        "metric_name": metric_name,
                        "metric_value": metric_value,
                        "metric_unit": "count_or_percent",
                        "source": "configured_open_data",
                        "payload": row,
                    }
                )
        return self._dedupe(records)

    def _fetch_if_configured(self, env_name: str) -> list[dict]:
        url = (os.environ.get(env_name) or "").strip()
        if not url:
            return []
        try:
            return self.client.fetch_rows(url)
        except requests_exceptions() as err:
            logger.warning("Failed to fetch civic source %s from %s: %s", env_name, url, err)
            return []
        except ValueError as err:
            logger.warning("Failed to parse civic source %s from %s: %s", env_name, url, err)
            return []


    def _match_area_slug(self, neighbourhoods: list[dict], row: dict, lat: float | None, lon: float | None) -> str | None:
        names = [
            self._value(row, "neighbourhood", "neighbourhood_name", "area_name", "hood", "AREA_NAME"),
            self._value(row, "area", "community", "district"),
        ]
        for name in names:
            if not name:
                continue
            slug = slugify(str(name))
            for neighbourhood in neighbourhoods:
                if neighbourhood["slug"] == slug:
                    return slug
        if lat is None or lon is None:
            return None
        candidates = [n for n in neighbourhoods if n.get("latitude") is not None and n.get("longitude") is not None]
        if not candidates:
            return None
        closest = min(
            candidates,
            key=lambda n: ((float(n["latitude"]) - lat) ** 2) + ((float(n["longitude"]) - lon) ** 2),
        )
        return closest["slug"]

    def _extract_lat(self, row: dict) -> float | None:
        geometry = row.get("geometry") if isinstance(row, dict) else None
        if isinstance(geometry, dict):
            coords = geometry.get("coordinates")
            if isinstance(coords, list) and len(coords) >= 2:
                if isinstance(coords[0], list) and coords[0]:
                    point = coords[0][0]
                    if isinstance(point, list) and len(point) >= 2:
                        return safe_float(point[1])
                return safe_float(coords[1])
        return safe_float(self._value(row, "latitude", "lat", "LATITUDE", "y"))

    def _extract_lon(self, row: dict) -> float | None:
        geometry = row.get("geometry") if isinstance(row, dict) else None
        if isinstance(geometry, dict):
            coords = geometry.get("coordinates")
            if isinstance(coords, list) and len(coords) >= 2:
                if isinstance(coords[0], list) and coords[0]:
                    point = coords[0][0]
                    if isinstance(point, list) and len(point) >= 2:
                        return safe_float(point[0])
                return safe_float(coords[0])
        return safe_float(self._value(row, "longitude", "lon", "LONGITUDE", "x"))

    def _value(self, row: dict, *keys: str):
        for key in keys:
            if key in row and row[key] not in (None, ""):
                return row[key]
        return None

    def _dedupe(self, rows: list[dict]) -> list[dict]:
        deduped: dict[str, dict] = {}
        for row in rows:
            deduped[row["id"]] = row
        return list(deduped.values())


def requests_exceptions():
    import requests

    return requests.RequestException
