from __future__ import annotations

from real_estate_app.repositories import search_repository


def vector_search(query: str, top_k: int = 5) -> dict:
    return search_repository.vector_search(query, top_k)
