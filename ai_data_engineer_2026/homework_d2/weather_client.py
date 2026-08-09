"""NWS weather client for harvesting unstructured weather text."""

from __future__ import annotations

import hashlib
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

import requests

BASE_URL = os.environ.get("WEATHER_SOURCE_BASE_URL", "https://api.weather.gov").rstrip("/")
USER_AGENT = os.environ.get("WEATHER_USER_AGENT", "weather-intelligence/1.0 (contact@example.com)")


@dataclass(frozen=True)
class WeatherDocument:
    id: str
    location: str
    source_type: str
    headline: str
    narrative_text: str
    issued_at: str | None
    effective_at: str | None
    payload: dict[str, Any]


class WeatherClient:
    def __init__(self, base_url: str | None = None, user_agent: str | None = None, timeout: int = 30):
        self.base_url = (base_url or BASE_URL).rstrip("/")
        self.timeout = timeout
        self._session = requests.Session()
        self._session.headers.update(
            {
                "User-Agent": user_agent or USER_AGENT,
                "Accept": "application/geo+json, application/json",
            }
        )

    def _get(self, path: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        resp = self._session.get(f"{self.base_url}{path}", params=params, timeout=self.timeout)
        resp.raise_for_status()
        return resp.json()

    def resolve_location(self, location: str) -> dict[str, Any]:
        query = location.strip()
        if "," in query and any(ch.isdigit() for ch in query):
            lat, lon = self._parse_latlon(query)
        else:
            if "canada" in query.lower():
                raise ValueError(
                    f"Location is outside api.weather.gov coverage: {query}. The current weather source supports U.S. locations only."
                )
            lat, lon = self._geocode_location(query)
        try:
            return self._get(f"/points/{lat},{lon}")
        except requests.HTTPError as err:
            if err.response is not None and err.response.status_code == 404:
                raise ValueError(
                    f"Location is outside api.weather.gov coverage: {query}. The current weather source supports U.S. locations only."
                ) from err
            raise

    def fetch_documents(self, location: str, limit: int = 50) -> list[WeatherDocument]:
        point = self.resolve_location(location)
        props = point.get("properties", {})
        office = props.get("cwa")
        grid_x = props.get("gridX")
        grid_y = props.get("gridY")
        rel = props.get("relativeLocation", {}).get("properties", {})
        location_label = ", ".join(
            part for part in [rel.get("city"), rel.get("state")] if part
        ) or location
        coordinates = point.get("geometry", {}).get("coordinates", [None, None])
        lon = coordinates[0] if len(coordinates) > 0 else None
        lat = coordinates[1] if len(coordinates) > 1 else None

        documents: list[WeatherDocument] = []
        documents.extend(self._fetch_alerts(location_label, lat, lon, limit))
        documents.extend(self._fetch_forecast(location_label, office, grid_x, grid_y))
        documents.extend(self._fetch_forecast_discussion(location_label, office))
        return documents

    def _geocode_location(self, query: str) -> tuple[float, float]:
        response = self._session.get(
            "https://geocoding-api.open-meteo.com/v1/search",
            params={"name": query, "count": 1, "language": "en", "format": "json"},
            timeout=self.timeout,
        )
        response.raise_for_status()
        results = response.json().get("results", [])
        if not results:
            raise ValueError(f"Unable to geocode location: {query}")
        return float(results[0]["latitude"]), float(results[0]["longitude"])

    def _parse_latlon(self, query: str) -> tuple[float, float]:
        parts = [p.strip() for p in query.split(",")]
        if len(parts) != 2:
            raise ValueError(f"Invalid lat/lon location: {query}")
        return float(parts[0]), float(parts[1])

    def _fetch_alerts(self, location_label: str, lat: float | None, lon: float | None, limit: int) -> list[WeatherDocument]:
        params: dict[str, Any] = {"limit": limit}
        if lat is not None and lon is not None:
            params["point"] = f"{lat},{lon}"
        try:
            data = self._get("/alerts/active", params=params)
        except requests.HTTPError as err:
            if err.response is not None and err.response.status_code == 400 and "point" in params:
                return []
            raise
        alerts = data.get("features", [])[:limit]
        docs: list[WeatherDocument] = []
        for alert in alerts:
            props = alert.get("properties", {})
            narrative = "\n".join(
                part for part in [props.get("headline"), props.get("description"), props.get("instruction")] if part
            ).strip()
            docs.append(
                WeatherDocument(
                    id=props.get("id") or self._stable_id("alert", location_label, props.get("event"), props.get("sent"), props.get("effective")),
                    location=location_label,
                    source_type="alert",
                    headline=props.get("event") or props.get("headline") or "Weather Alert",
                    narrative_text=narrative or props.get("description") or "",
                    issued_at=props.get("sent"),
                    effective_at=props.get("effective"),
                    payload=alert,
                )
            )
        return docs

    def _fetch_forecast(self, location_label: str, office: str | None, grid_x: int | None, grid_y: int | None) -> list[WeatherDocument]:
        if not office or grid_x is None or grid_y is None:
            return []
        data = self._get(f"/gridpoints/{office}/{grid_x},{grid_y}/forecast")
        periods = data.get("properties", {}).get("periods", [])
        docs: list[WeatherDocument] = []
        for period in periods:
            narrative = period.get("detailedForecast") or period.get("shortForecast") or ""
            docs.append(
                WeatherDocument(
                    id=self._stable_id("forecast", location_label, period.get("number"), period.get("startTime")),
                    location=location_label,
                    source_type="forecast",
                    headline=period.get("name") or period.get("shortForecast") or "Forecast",
                    narrative_text=narrative,
                    issued_at=period.get("startTime"),
                    effective_at=period.get("startTime"),
                    payload=period,
                )
            )
        return docs

    def _fetch_forecast_discussion(self, location_label: str, office: str | None) -> list[WeatherDocument]:
        if not office:
            return []

        collection = self._get(f"/products/types/AFD/locations/{office}")
        products = collection.get("@graph", [])
        if not products:
            return []

        latest = max(products, key=lambda item: item.get("issuanceTime") or "")
        product_id = latest.get("id")
        if not product_id:
            return []

        product = self._get(f"/products/{product_id}")
        narrative = (product.get("productText") or "").strip()
        if not narrative:
            return []

        issued_at = product.get("issuanceTime")
        return [
            WeatherDocument(
                id=self._stable_id("discussion", location_label, office, product_id),
                location=location_label,
                source_type="discussion",
                headline=product.get("productName") or "Area Forecast Discussion",
                narrative_text=narrative,
                issued_at=issued_at,
                effective_at=issued_at,
                payload=product,
            )
        ]

    def get_hourly_forecast(self, location: str, limit: int = 24) -> list[WeatherDocument]:
        point = self.resolve_location(location)
        props = point.get("properties", {})
        office = props.get("cwa")
        grid_x = props.get("gridX")
        grid_y = props.get("gridY")
        rel = props.get("relativeLocation", {}).get("properties", {})
        location_label = ", ".join(part for part in [rel.get("city"), rel.get("state")] if part) or location
        if not office or grid_x is None or grid_y is None:
            return []
        data = self._get(f"/gridpoints/{office}/{grid_x},{grid_y}/forecast/hourly")
        periods = data.get("properties", {}).get("periods", [])[:limit]
        docs: list[WeatherDocument] = []
        for period in periods:
            narrative = period.get("detailedForecast") or period.get("shortForecast") or ""
            docs.append(
                WeatherDocument(
                    id=self._stable_id("hourly", location_label, period.get("number"), period.get("startTime")),
                    location=location_label,
                    source_type="forecast_hourly",
                    headline=period.get("name") or period.get("shortForecast") or "Hourly Forecast",
                    narrative_text=narrative,
                    issued_at=period.get("startTime"),
                    effective_at=period.get("startTime"),
                    payload=period,
                )
            )
        return docs

    def _stable_id(self, *parts: object) -> str:
        raw = "|".join(str(p) for p in parts if p is not None)
        return hashlib.sha1(raw.encode("utf-8")).hexdigest()


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()
