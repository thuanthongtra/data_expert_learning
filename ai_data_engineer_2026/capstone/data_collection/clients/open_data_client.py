from __future__ import annotations

import csv
import io
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup


class OpenDataClient:
    def __init__(self, timeout: int = 60):
        self.timeout = timeout
        self._session = requests.Session()
        self._session.headers.update({"User-Agent": "north-york-real-estate-copilot/1.0"})

    def fetch_rows(self, url: str) -> list[dict]:
        resp = self._session.get(url, timeout=self.timeout)
        resp.raise_for_status()
        content_type = (resp.headers.get("Content-Type") or "").lower()
        path = urlparse(url).path.lower()
        if "text/html" in content_type or path.endswith("/"):
            resource_url = self._extract_resource_url(resp.text, url)
            if resource_url and resource_url != url:
                return self.fetch_rows(resource_url)
            return []
        if "json" in content_type or path.endswith(".json"):
            payload = resp.json()
            if isinstance(payload, list):
                return [row for row in payload if isinstance(row, dict)]
            if isinstance(payload, dict):
                for key in ("data", "results", "features", "records"):
                    value = payload.get(key)
                    if isinstance(value, list):
                        if key == "features":
                            return [self._feature_to_row(feature) for feature in value]
                        return [row for row in value if isinstance(row, dict)]
            return []
        text = resp.text
        return list(csv.DictReader(io.StringIO(text)))

    def _extract_resource_url(self, html: str, base_url: str) -> str | None:
        soup = BeautifulSoup(html, "html.parser")
        links = []
        for anchor in soup.find_all("a", href=True):
            href = anchor["href"].strip()
            if not href:
                continue
            text = anchor.get_text(" ", strip=True).lower()
            if any(token in href.lower() for token in (".csv", ".geojson", ".json", "download")) or any(
                token in text for token in ("csv", "geojson", "json", "download")
            ):
                links.append(requests.compat.urljoin(base_url, href))
        for suffix in (".geojson", ".json", ".csv"):
            for link in links:
                if suffix in link.lower():
                    return link
        return links[0] if links else None

    def _feature_to_row(self, feature: dict) -> dict:
        properties = feature.get("properties") if isinstance(feature, dict) else None
        geometry = feature.get("geometry") if isinstance(feature, dict) else None
        row = dict(properties or {})
        if geometry:
            row["geometry"] = geometry
        return row
