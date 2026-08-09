# Databricks notebook source
# /// script
# [tool.databricks.environment]
# environment_version = "5"
# dependencies = [
#   "sentence-transformers",
#   "psycopg2-binary",
#   "databricks-sdk>=0.118.0",
#   "pgvector",
#   "sqlalchemy",
# ]
# ///

"""Plain Python ingestion script for weather document embeddings."""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path

from psycopg2.extras import execute_values

from ai_data_engineer_2026.homework_d2 import lakebase
from ai_data_engineer_2026.homework_d2.weather_client import WeatherClient


def _load_env_example() -> None:
    module_file = globals().get("__file__")
    candidate_roots = [Path(module_file).resolve().parents[1]] if module_file else [Path.cwd(), *Path.cwd().parents]

    env_path = next((root / ".env.example" for root in candidate_roots if (root / ".env.example").exists()), None)
    if env_path is None:
        return

    for line in env_path.read_text().splitlines():
        raw_line = line.strip()
        if not raw_line or raw_line.startswith("#") or "=" not in raw_line:
            continue
        key, value = raw_line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip())


_load_env_example()

MODEL_NAME = os.environ.get("WEATHER_EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
CHUNK_SIZE = int(os.environ.get("WEATHER_CHUNK_SIZE", "800"))
CHUNK_OVERLAP = int(os.environ.get("WEATHER_CHUNK_OVERLAP", "100"))
WEATHER_SYNC_LIMIT = int(os.environ.get("WEATHER_SYNC_LIMIT", "50"))


def chunk_text(text: str, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> list[str]:
    text = (text or "").strip()
    if not text:
        return []
    if len(text) <= chunk_size:
        return [text]

    chunks = []
    step = max(1, chunk_size - overlap)
    for start in range(0, len(text), step):
        chunk = text[start : start + chunk_size].strip()
        if chunk:
            chunks.append(chunk)
        if start + chunk_size >= len(text):
            break
    return chunks


def _weather_sync_locations() -> list[str]:
    raw_value = os.environ.get("WEATHER_SYNC_LOCATIONS", "")
    return [location.strip() for location in raw_value.split(";") if location.strip()]


def _get_unembedded_documents() -> list[dict]:
    return lakebase.run_query(
        """
        SELECT id, narrative_text
        FROM weather_documents
        WHERE id NOT IN (SELECT DISTINCT document_id FROM weather_embeddings)
        ORDER BY synced_at ASC
        """
    )


def _upsert_documents(docs: list) -> int:
    if not docs:
        return 0

    count = 0
    with lakebase.get_connection() as conn:
        with conn.cursor() as cur:
            for doc in docs:
                cur.execute(
                    """
                    INSERT INTO weather_documents (
                        id, location, source_type, headline, narrative_text,
                        issued_at, effective_at, payload, synced_at
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, now())
                    ON CONFLICT (id) DO UPDATE
                        SET location = EXCLUDED.location,
                            source_type = EXCLUDED.source_type,
                            headline = EXCLUDED.headline,
                            narrative_text = EXCLUDED.narrative_text,
                            issued_at = EXCLUDED.issued_at,
                            effective_at = EXCLUDED.effective_at,
                            payload = EXCLUDED.payload,
                            synced_at = EXCLUDED.synced_at
                    """,
                    (
                        doc.id,
                        doc.location,
                        doc.source_type,
                        doc.headline,
                        doc.narrative_text,
                        doc.issued_at,
                        doc.effective_at,
                        json.dumps(doc.payload),
                    ),
                )
                count += 1
            conn.commit()
    return count


def _bootstrap_weather_documents() -> int:
    locations = _weather_sync_locations()
    if not locations:
        return 0

    client = WeatherClient()
    synced = 0
    for location in locations:
        try:
            synced += _upsert_documents(client.fetch_documents(location, limit=max(1, WEATHER_SYNC_LIMIT)))
        except Exception as err:
            print(f"Skipping location {location}: {err}")
    return synced


def _require_ingestion_tables() -> None:
    rows = lakebase.run_query(
        """
        SELECT
            to_regclass('public.weather_documents') AS weather_documents,
            to_regclass('public.weather_embeddings') AS weather_embeddings
        """
    )
    row = rows[0] if rows else {}
    missing = [
        table_name
        for table_name in ("weather_documents", "weather_embeddings")
        if not row.get(table_name)
    ]
    if missing:
        missing_list = ", ".join(missing)
        raise RuntimeError(
            f"Missing required table(s): {missing_list}. Create the schema with a role that owns the tables before running ingestion."
        )


def main() -> None:
    _require_ingestion_tables()

    docs = _get_unembedded_documents()

    if not docs:
        synced = _bootstrap_weather_documents()
        if synced:
            docs = _get_unembedded_documents()

    if not docs:
        locations = _weather_sync_locations()
        if locations:
            print(
                f"No weather documents are available to embed after syncing configured locations: {', '.join(locations)}."
            )
        else:
            print(
                "No weather documents are available to embed. Set WEATHER_SYNC_LOCATIONS to a semicolon-separated list such as 'Chicago, IL;Austin, TX' and rerun this file."
            )
        return

    from sentence_transformers import SentenceTransformer

    model = SentenceTransformer(MODEL_NAME)

    rows = []
    for doc in docs:
        chunks = chunk_text(doc["narrative_text"])
        vectors = model.encode(chunks, normalize_embeddings=True).tolist() if chunks else []
        for idx, (chunk, vector) in enumerate(zip(chunks, vectors)):
            rows.append(
                (
                    f"{doc['id']}_{idx}",
                    doc["id"],
                    idx,
                    chunk,
                    json.dumps(vector),
                    MODEL_NAME,
                    datetime.now(timezone.utc),
                )
                )

    if not rows:
        print("No chunk rows produced.")
        return

    with lakebase.get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM weather_embeddings WHERE document_id = ANY(%s)", ([row[1] for row in rows],))
        conn.commit()

    with lakebase.get_connection() as conn:
        with conn.cursor() as cur:
            execute_values(
                cur,
                """
                INSERT INTO weather_embeddings (
                    id, document_id, chunk_index, chunk_text, embedding, model_name, created_at
                ) VALUES %s
                ON CONFLICT (id) DO UPDATE
                    SET document_id = EXCLUDED.document_id,
                        chunk_index = EXCLUDED.chunk_index,
                        chunk_text = EXCLUDED.chunk_text,
                        embedding = EXCLUDED.embedding,
                        model_name = EXCLUDED.model_name,
                        created_at = EXCLUDED.created_at
                """,
                rows,
                template="(%s, %s, %s, %s, %s::vector, %s, %s)",
                page_size=100,
            )
        conn.commit()

    print(f"Upserted {len(rows)} weather embeddings.")


if __name__ == "__main__":
    main()
