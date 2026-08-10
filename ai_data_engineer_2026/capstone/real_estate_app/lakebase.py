"""Shared Lakebase/Postgres helper for the real-estate project."""

from __future__ import annotations

import base64
import binascii
import logging
import os
from contextlib import contextmanager

import psycopg2
from databricks.sdk import WorkspaceClient
from psycopg2 import errorcodes
from psycopg2.extras import RealDictCursor

try:
    from pgvector.psycopg2 import register_vector
except ModuleNotFoundError:
    register_vector = None

try:
    from sqlalchemy import create_engine
except ModuleNotFoundError:
    create_engine = None

from real_estate_app.config import SQL_DIR

logger = logging.getLogger("real-estate-lakebase")
_workspace_client: WorkspaceClient | None = None

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

    secret = _get_workspace_client().secrets.get_secret(scope=_SECRET_SCOPE, key=_SECRET_KEY)
    return _normalize_connection_string(secret.value)


def _get_workspace_client() -> WorkspaceClient:
    global _workspace_client
    if _workspace_client is None:
        _workspace_client = WorkspaceClient()
    return _workspace_client


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


def run_write_returning(sql: str, params: tuple | dict | None = None) -> dict | None:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            row = cur.fetchone()
            conn.commit()
            return row


def _safe_execute(sql: str) -> None:
    try:
        run_write(sql)
    except psycopg2.Error as err:
        if getattr(err, "pgcode", None) == errorcodes.INSUFFICIENT_PRIVILEGE:
            logger.warning("Skipping DDL due to insufficient privilege: %s", err)
            return
        raise


def ensure_schema() -> None:
    for file_path in sorted(SQL_DIR.glob("*.sql")):
        _safe_execute(file_path.read_text(encoding="utf-8"))
