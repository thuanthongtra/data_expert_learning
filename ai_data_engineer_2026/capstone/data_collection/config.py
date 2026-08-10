from __future__ import annotations

import json
import os


CHUNK_SIZE = int(os.environ.get("REAL_ESTATE_CHUNK_SIZE", "800"))
CHUNK_OVERLAP = int(os.environ.get("REAL_ESTATE_CHUNK_OVERLAP", "100"))
WEB_DOCUMENT_TIMEOUT = int(os.environ.get("WEB_DOCUMENT_TIMEOUT", "30"))

CURATED_NEIGHBOURHOODS = [
    "Willowdale East",
    "Willowdale West",
    "Lansing-Westgate",
    "Bayview Village",
    "Don Valley Village",
    "York Mills",
    "Newtonbrook East",
    "Newtonbrook West",
    "Bathurst Manor",
    "Clanton Park",
    "Downsview",
    "Don Mills",
    "Hillcrest Village",
    "Westminster-Branson",
]

CURATED_MARKET_DOCUMENTS = [
    {
        "doc_type": "area_profile",
        "area_slug": "north-york",
        "publisher": "Wikipedia",
        "source_url": "https://en.wikipedia.org/wiki/North_York",
    },
    {
        "doc_type": "area_profile",
        "area_slug": "willowdale-east",
        "publisher": "Wikipedia",
        "source_url": "https://en.wikipedia.org/wiki/Willowdale,_Toronto",
    },
    {
        "doc_type": "area_profile",
        "area_slug": "don-mills",
        "publisher": "Wikipedia",
        "source_url": "https://en.wikipedia.org/wiki/Don_Mills",
    },
    {
        "doc_type": "area_profile",
        "area_slug": "bayview-village",
        "publisher": "Wikipedia",
        "source_url": "https://en.wikipedia.org/wiki/Bayview_Village",
    },
]


def configured_market_documents() -> list[dict]:
    raw = (os.environ.get("REAL_ESTATE_MARKET_DOCUMENTS_JSON") or "").strip()
    if not raw:
        return CURATED_MARKET_DOCUMENTS
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        return CURATED_MARKET_DOCUMENTS
    if not isinstance(parsed, list):
        return CURATED_MARKET_DOCUMENTS
    documents = [row for row in parsed if isinstance(row, dict) and row.get("source_url")]
    return documents or CURATED_MARKET_DOCUMENTS


def configured_civic_sources() -> dict[str, str]:
    return {
        "crime": (os.environ.get("TORONTO_CRIME_SOURCE_URL") or "").strip(),
        "development": (os.environ.get("TORONTO_DEVELOPMENT_SOURCE_URL") or "").strip(),
        "zoning": (os.environ.get("TORONTO_ZONING_SOURCE_URL") or "").strip(),
        "demographics": (os.environ.get("TORONTO_DEMOGRAPHICS_SOURCE_URL") or "").strip(),
    }
