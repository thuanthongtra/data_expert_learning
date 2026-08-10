from __future__ import annotations

import os

import requests


class BankOfCanadaClient:
    def __init__(self, timeout: int = 30):
        self.timeout = timeout
        self._session = requests.Session()
        self._session.headers.update({"User-Agent": "north-york-real-estate-copilot/1.0"})

    def get_series_observations(self, series_name: str, recent: int = 30) -> list[dict]:
        url = f"https://www.bankofcanada.ca/valet/observations/{series_name}/json"
        resp = self._session.get(url, params={"recent": recent}, timeout=self.timeout)
        resp.raise_for_status()
        payload = resp.json()
        return payload.get("observations", [])

    def configured_series(self) -> list[str]:
        raw = os.environ.get("BANK_OF_CANADA_SERIES", "V39079")
        return [item.strip() for item in raw.split(",") if item.strip()]
