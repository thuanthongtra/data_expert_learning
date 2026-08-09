"""Weather API adapter for the Assignment 3 MCP server."""

from __future__ import annotations

import math
import os
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from typing import Any

import requests

OPEN_METEO_GEOCODING_URL = os.environ.get("WEATHER_GEOCODING_URL", "https://geocoding-api.open-meteo.com/v1/search")
OPEN_METEO_FORECAST_URL = os.environ.get("WEATHER_FORECAST_URL", "https://api.open-meteo.com/v1/forecast")
DEFAULT_TIMEOUT = int(os.environ.get("WEATHER_API_TIMEOUT", "30"))
DEFAULT_DAYS = 3
MAX_DAYS = 7

WEATHER_CODE_MAP: dict[int, str] = {
    0: "Clear",
    1: "Mainly clear",
    2: "Partly cloudy",
    3: "Overcast",
    45: "Fog",
    48: "Depositing rime fog",
    51: "Light drizzle",
    53: "Moderate drizzle",
    55: "Dense drizzle",
    61: "Light rain",
    63: "Moderate rain",
    65: "Heavy rain",
    71: "Light snow",
    73: "Moderate snow",
    75: "Heavy snow",
    80: "Rain showers",
    81: "Rain showers",
    82: "Violent rain showers",
    95: "Thunderstorm",
    96: "Thunderstorm with hail",
    99: "Thunderstorm with heavy hail",
}


@dataclass(frozen=True)
class ResolvedLocation:
    label: str
    latitude: float
    longitude: float
    timezone: str


class WeatherBroker:
    def __init__(self, timeout: int = DEFAULT_TIMEOUT):
        self.timeout = timeout
        self._session = requests.Session()
        self._session.headers.update({"User-Agent": os.environ.get("WEATHER_USER_AGENT", "weather-mcp-server/1.0")})

    def _get(self, url: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        resp = self._session.get(url, params=params, timeout=self.timeout)
        resp.raise_for_status()
        return resp.json()

    def resolve_location(self, location: str) -> ResolvedLocation:
        query = (location or "").strip()
        if not query:
            raise ValueError("location is required")

        if self._looks_like_latlon(query):
            latitude, longitude = self._parse_latlon(query)
            return ResolvedLocation(label=query, latitude=latitude, longitude=longitude, timezone="auto")

        data = self._get(
            OPEN_METEO_GEOCODING_URL,
            params={"name": query, "count": 1, "language": "en", "format": "json"},
        )
        results = data.get("results") or []
        if not results:
            raise ValueError(f"Unable to resolve location: {query}")

        first = results[0]
        label_parts = [first.get("name"), first.get("admin1"), first.get("country")]
        label = ", ".join(part for part in label_parts if part)
        return ResolvedLocation(
            label=label or query,
            latitude=float(first["latitude"]),
            longitude=float(first["longitude"]),
            timezone=str(first.get("timezone") or "auto"),
        )

    def get_current_weather(self, location: str) -> dict[str, Any]:
        resolved = self.resolve_location(location)
        data = self._get(
            OPEN_METEO_FORECAST_URL,
            params={
                "latitude": resolved.latitude,
                "longitude": resolved.longitude,
                "current": "temperature_2m,apparent_temperature,relative_humidity_2m,wind_speed_10m,wind_direction_10m,weather_code",
                "timezone": resolved.timezone,
            },
        )
        current = data.get("current") or {}
        return {
            "location": resolved.label,
            "resolved": {
                "latitude": resolved.latitude,
                "longitude": resolved.longitude,
                "source": "open-meteo",
            },
            "current": {
                "temperature_c": current.get("temperature_2m"),
                "temperature_f": self._c_to_f(current.get("temperature_2m")),
                "apparent_temperature_c": current.get("apparent_temperature"),
                "apparent_temperature_f": self._c_to_f(current.get("apparent_temperature")),
                "humidity_percent": current.get("relative_humidity_2m"),
                "wind_speed_kph": current.get("wind_speed_10m"),
                "wind_speed_mph": self._kph_to_mph(current.get("wind_speed_10m")),
                "wind_direction_degrees": current.get("wind_direction_10m"),
                "condition": self._weather_code_label(current.get("weather_code")),
                "observation_time": current.get("time"),
            },
        }

    def get_forecast(self, location: str, days: int = DEFAULT_DAYS) -> dict[str, Any]:
        resolved = self.resolve_location(location)
        days = self._clamp_days(days)
        data = self._get(
            OPEN_METEO_FORECAST_URL,
            params={
                "latitude": resolved.latitude,
                "longitude": resolved.longitude,
                "daily": "temperature_2m_max,temperature_2m_min,precipitation_probability_max,wind_speed_10m_max,weather_code",
                "forecast_days": days,
                "timezone": resolved.timezone,
            },
        )
        daily = data.get("daily") or {}
        times = daily.get("time") or []
        forecasts = []
        for index, day in enumerate(times[:days]):
            high_c = self._safe_index(daily.get("temperature_2m_max"), index)
            low_c = self._safe_index(daily.get("temperature_2m_min"), index)
            wind_kph = self._safe_index(daily.get("wind_speed_10m_max"), index)
            precip = self._safe_index(daily.get("precipitation_probability_max"), index)
            code = self._safe_index(daily.get("weather_code"), index)
            forecasts.append(
                {
                    "date": day,
                    "temp_high_c": high_c,
                    "temp_high_f": self._c_to_f(high_c),
                    "temp_low_c": low_c,
                    "temp_low_f": self._c_to_f(low_c),
                    "precipitation_probability_percent": precip,
                    "wind_speed_kph": wind_kph,
                    "wind_speed_mph": self._kph_to_mph(wind_kph),
                    "condition": self._weather_code_label(code),
                }
            )
        return {
            "location": resolved.label,
            "resolved": {
                "latitude": resolved.latitude,
                "longitude": resolved.longitude,
                "source": "open-meteo",
            },
            "days": days,
            "forecast": forecasts,
        }

    def recommend_for_weather(self, location: str, target_date: str | None = None) -> dict[str, Any]:
        forecast = self.get_forecast(location, days=MAX_DAYS)
        day = self._select_day(forecast["forecast"], target_date)
        if day is None:
            raise ValueError("No forecast data available for the requested date")

        precipitation = self._as_number(day.get("precipitation_probability_percent")) or 0.0
        temp_c = self._as_number(day.get("temp_high_c"))
        wind_kph = self._as_number(day.get("wind_speed_kph")) or 0.0

        signals: list[str] = []
        recommendation_parts: list[str] = []

        if precipitation >= 40:
            recommendation_parts.append("bring an umbrella")
            signals.append(f"precipitation probability is {precipitation:.0f}%")
        if temp_c is not None and temp_c <= 15:
            recommendation_parts.append("wear a light jacket")
            signals.append(f"temperature is {temp_c:.1f}C")
        if wind_kph >= 35:
            recommendation_parts.append("expect windy conditions")
            signals.append(f"wind speed is {wind_kph:.1f} kph")

        if not recommendation_parts:
            recommendation = "Weather looks fine for normal outdoor plans"
            reasoning = "Rain chance is low and winds are moderate."
        else:
            recommendation = ", ".join(dict.fromkeys(recommendation_parts)).capitalize()
            reasoning = "; ".join(signals)

        return {
            "location": forecast["location"],
            "date": day.get("date"),
            "recommendation": recommendation,
            "reasoning": reasoning,
            "signals": {
                "temperature_c": day.get("temp_high_c"),
                "temperature_f": day.get("temp_high_f"),
                "wind_speed_kph": day.get("wind_speed_kph"),
                "wind_speed_mph": day.get("wind_speed_mph"),
                "precipitation_probability_percent": day.get("precipitation_probability_percent"),
                "condition": day.get("condition"),
            },
        }

    def _select_day(self, forecast_rows: list[dict[str, Any]], target_date: str | None) -> dict[str, Any] | None:
        if not forecast_rows:
            return None
        if target_date:
            try:
                wanted = date.fromisoformat(target_date)
            except ValueError as err:
                raise ValueError(f"Invalid date: {target_date}. Use YYYY-MM-DD.") from err
            for row in forecast_rows:
                if row.get("date") == wanted.isoformat():
                    return row
        return forecast_rows[0]

    @staticmethod
    def _looks_like_latlon(value: str) -> bool:
        parts = [part.strip() for part in value.split(",")]
        if len(parts) != 2:
            return False
        try:
            float(parts[0])
            float(parts[1])
            return True
        except ValueError:
            return False

    @staticmethod
    def _parse_latlon(value: str) -> tuple[float, float]:
        lat_str, lon_str = [part.strip() for part in value.split(",")]
        return float(lat_str), float(lon_str)

    @staticmethod
    def _c_to_f(value: float | int | None) -> float | None:
        if value is None:
            return None
        return round((float(value) * 9 / 5) + 32, 1)

    @staticmethod
    def _kph_to_mph(value: float | int | None) -> float | None:
        if value is None:
            return None
        return round(float(value) * 0.621371, 1)

    @staticmethod
    def _safe_index(values: list[Any] | None, index: int) -> Any:
        if not values or index >= len(values):
            return None
        return values[index]

    @staticmethod
    def _as_number(value: Any) -> float | None:
        if value is None:
            return None
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _clamp_days(days: int) -> int:
        try:
            value = int(days)
        except Exception:
            value = DEFAULT_DAYS
        return max(1, min(MAX_DAYS, value))

    @staticmethod
    def _weather_code_label(code: Any) -> str:
        if code is None:
            return "Unknown"
        try:
            return WEATHER_CODE_MAP.get(int(code), f"Weather code {int(code)}")
        except (TypeError, ValueError):
            return "Unknown"
