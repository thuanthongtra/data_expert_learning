from __future__ import annotations

from sentence_transformers import SentenceTransformer

from real_estate_app.config import DEFAULT_MODEL_NAME, table_name
from real_estate_app.lakebase import run_query

_model: SentenceTransformer | None = None


def get_embedding_model() -> SentenceTransformer:
    global _model
    if _model is None:
        _model = SentenceTransformer(DEFAULT_MODEL_NAME)
    return _model


def vector_search(query: str, top_k: int = 5) -> dict:
    top_k = max(1, min(20, int(top_k)))
    query_embedding = get_embedding_model().encode(query, normalize_embeddings=True).tolist()
    rows = run_query(
        f"""
        WITH ranked_matches AS (
            SELECT
                d.id,
                d.doc_type,
                d.title,
                d.source_url,
                d.publisher,
                d.area_slug,
                d.published_at,
                d.text_content,
                e.chunk_text,
                e.chunk_index,
                1 - (e.embedding <=> q.query_vector) AS similarity,
                ROW_NUMBER() OVER (
                    PARTITION BY d.id
                    ORDER BY e.embedding <=> q.query_vector
                ) AS doc_rank
            FROM {table_name('market_embeddings')} e
            JOIN {table_name('market_documents')} d ON d.id = e.document_id
            CROSS JOIN (SELECT %s::vector AS query_vector) q
        )
        SELECT id, doc_type, title, source_url, publisher, area_slug, published_at, text_content, chunk_text, chunk_index, similarity
        FROM ranked_matches
        WHERE doc_rank = 1
        ORDER BY similarity DESC
        LIMIT %s
        """,
        (str(query_embedding), top_k),
    )
    matches = []
    for row in rows:
        similarity = float(row.get("similarity") or 0.0)
        matches.append({**row, "similarity_percent": round(max(0.0, min(1.0, similarity)) * 100, 2)})
    return {"query": query, "top_k": top_k, "matches": matches}
