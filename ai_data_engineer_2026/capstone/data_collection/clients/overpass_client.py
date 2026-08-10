from __future__ import annotations

import os

import requests


class OverpassClient:
    def __init__(self, base_url: str | None = None, timeout: int = 60):
        self.base_url = base_url or os.environ.get("OVERPASS_URL", "https://overpass-api.de/api/interpreter")
        self.timeout = timeout
        self._session = requests.Session()
        self._session.headers.update({"User-Agent": "north-york-real-estate-copilot/1.0"})

    def query(self, overpass_ql: str) -> list[dict]:
        resp = self._session.post(self.base_url, data=overpass_ql.encode("utf-8"), timeout=self.timeout)
        resp.raise_for_status()
        payload = resp.json()
        return payload.get("elements", [])
