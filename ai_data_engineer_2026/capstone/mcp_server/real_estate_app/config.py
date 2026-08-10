from __future__ import annotations

import os
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SQL_DIR = PROJECT_ROOT / "sql"
DEFAULT_SCHEMA = os.environ.get("REAL_ESTATE_SCHEMA", "realestate")
DEFAULT_MODEL_NAME = os.environ.get(
    "REAL_ESTATE_EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2"
)
DEFAULT_GEOGRAPHY = os.environ.get("REAL_ESTATE_GEOGRAPHY", "North York")
DEFAULT_CITY = os.environ.get("REAL_ESTATE_CITY", "Toronto")
DEFAULT_PROVINCE = os.environ.get("REAL_ESTATE_PROVINCE", "Ontario")
DEFAULT_COUNTRY = os.environ.get("REAL_ESTATE_COUNTRY", "Canada")
DEFAULT_DELTA_CATALOG = os.environ.get("REAL_ESTATE_DELTA_CATALOG", "main")
DEFAULT_DELTA_SCHEMA = os.environ.get("REAL_ESTATE_DELTA_SCHEMA", "realestate_analytics")


def table_name(base_name: str) -> str:
    return f"{DEFAULT_SCHEMA}.{base_name}"


def delta_table_name(base_name: str) -> str:
    return f"{DEFAULT_DELTA_CATALOG}.{DEFAULT_DELTA_SCHEMA}.{base_name}"
