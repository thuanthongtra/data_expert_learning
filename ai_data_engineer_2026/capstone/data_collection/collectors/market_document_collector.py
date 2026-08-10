from __future__ import annotations

from data_collection.clients.web_document_client import WebDocumentClient
from data_collection.config import configured_market_documents
from data_collection.transformers.normalization import stable_id


class MarketDocumentCollector:
    def __init__(self):
        self.client = WebDocumentClient()

    def collect(self) -> list[dict]:
        documents = []
        for source in configured_market_documents():
            try:
                fetched = self.client.fetch(source["source_url"])
            except Exception:
                continue
            text_content = (fetched.get("text_content") or "").strip()
            if not text_content:
                continue
            documents.append(
                {
                    "id": stable_id("document", source["source_url"]),
                    "doc_type": source["doc_type"],
                    "area_slug": source.get("area_slug"),
                    "title": fetched.get("title") or source["source_url"],
                    "source_url": source["source_url"],
                    "publisher": source.get("publisher"),
                    "published_at": None,
                    "text_content": text_content,
                    "payload": {"source": source, "fetched_title": fetched.get("title")},
                }
            )
        return documents
