from __future__ import annotations

import os

import requests


class NominatimClient:
    def __init__(self, base_url: str | None = None, timeout: int = 30):
        self.base_url = base_url or os.environ.get("NOMINATIM_URL", "https://nominatim.openstreetmap.org/search")
        self.timeout = timeout
        self._session = requests.Session()
        self._session.headers.update(
            {"User-Agent": os.environ.get("NOMINATIM_USER_AGENT", "north-york-real-estate-copilot/1.0")}
        )

    def geocode(self, query: str) -> dict | None:
        resp = self._session.get(
            self.base_url,
            params={"q": query, "format": "jsonv2", "limit": 1},
            timeout=self.timeout,
        )
        resp.raise_for_status()
        rows = resp.json()
        return rows[0] if rows else None
