from __future__ import annotations

import requests
from bs4 import BeautifulSoup

from data_collection.config import WEB_DOCUMENT_TIMEOUT


class WebDocumentClient:
    def __init__(self, timeout: int = WEB_DOCUMENT_TIMEOUT):
        self.timeout = timeout
        self._session = requests.Session()
        self._session.headers.update({"User-Agent": "north-york-real-estate-copilot/1.0"})

    def fetch(self, url: str) -> dict:
        resp = self._session.get(url, timeout=self.timeout)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        title = (soup.title.string.strip() if soup.title and soup.title.string else url)
        paragraphs = [p.get_text(" ", strip=True) for p in soup.find_all("p")]
        text_content = "\n\n".join(part for part in paragraphs if part)
        return {"title": title, "text_content": text_content, "raw_html": resp.text}
