"""Lakebase/Postgres helper for the weather intelligence homework."""

from __future__ import annotations

import base64
import binascii
import os
from contextlib import contextmanager

import psycopg2
from databricks.sdk import WorkspaceClient
from psycopg2.extras import RealDictCursor

try:
    from sqlalchemy import create_engine
except ModuleNotFoundError:
    create_engine = None

try:
    from pgvector.psycopg2 import register_vector
except ModuleNotFoundError:
    register_vector = None

_w = WorkspaceClient()

_SECRET_SCOPE = os.environ.get("LAKEBASE_SECRET_SCOPE", "database")
_SECRET_KEY = os.environ.get("LAKEBASE_SECRET_KEY", "lakebase_connection_string")


def _normalize_connection_string(value: str) -> str:
    value = (value or "").strip()
    if not value:
        return value
    if value.startswith(("postgres://", "postgresql://")):
        return value

    padded = value + "=" * (-len(value) % 4)
    try:
        decoded = base64.b64decode(padded, validate=True).decode("utf-8").strip()
    except (binascii.Error, UnicodeDecodeError):
        return value

    if decoded.startswith(("postgres://", "postgresql://")):
        return decoded
    return value


def _lakebase_url() -> str:
    direct = os.environ.get("LAKEBASE_CONNECTION_STRING")
    if direct:
        return _normalize_connection_string(direct)

    try:
        import streamlit as st

        if _SECRET_KEY in st.secrets:
            return _normalize_connection_string(str(st.secrets[_SECRET_KEY]))
        if "LAKEBASE_CONNECTION_STRING" in st.secrets:
            return _normalize_connection_string(str(st.secrets["LAKEBASE_CONNECTION_STRING"]))
    except Exception:
        pass

    secret = _w.secrets.get_secret(scope=_SECRET_SCOPE, key=_SECRET_KEY)
    return _normalize_connection_string(secret.value)


@contextmanager
def get_connection():
    conn = psycopg2.connect(_lakebase_url(), cursor_factory=RealDictCursor)
    try:
        if register_vector is not None:
            register_vector(conn)
        yield conn
    finally:
        conn.close()


def get_engine():
    if create_engine is None:
        raise ModuleNotFoundError("sqlalchemy is required to create an engine")
    return create_engine(_lakebase_url())


def run_query(sql: str, params: tuple | dict | None = None) -> list[dict]:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            return cur.fetchall()


def run_write(sql: str, params: tuple | dict | None = None) -> int:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            conn.commit()
            return cur.rowcount


def ensure_schema() -> None:
    run_write("CREATE EXTENSION IF NOT EXISTS vector")
    run_write(
        """
        CREATE TABLE IF NOT EXISTS weather_documents (
            id TEXT PRIMARY KEY,
            location TEXT NOT NULL,
            source_type TEXT NOT NULL,
            headline TEXT NOT NULL,
            narrative_text TEXT NOT NULL,
            issued_at TIMESTAMPTZ,
            effective_at TIMESTAMPTZ,
            payload JSONB NOT NULL,
            synced_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
        """
    )
    run_write(
        """
        CREATE TABLE IF NOT EXISTS weather_embeddings (
            id TEXT PRIMARY KEY,
            document_id TEXT NOT NULL REFERENCES weather_documents(id) ON DELETE CASCADE,
            chunk_index INT NOT NULL,
            chunk_text TEXT NOT NULL,
            embedding VECTOR(384) NOT NULL,
            model_name TEXT NOT NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
        """
    )
    run_write(
        "CREATE INDEX IF NOT EXISTS idx_weather_embeddings_document_id ON weather_embeddings (document_id)"
    )
    run_write(
        "CREATE INDEX IF NOT EXISTS idx_weather_embeddings_embedding_hnsw ON weather_embeddings USING hnsw (embedding vector_cosine_ops)"
    )
    run_write(
        "CREATE INDEX IF NOT EXISTS idx_weather_documents_location ON weather_documents (location)"
    )
