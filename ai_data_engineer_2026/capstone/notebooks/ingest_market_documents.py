# Databricks notebook source
# DBTITLE 1,Cell 1
"""Spark bronze/silver ingestion for market and neighborhood documents."""

from __future__ import annotations

import json
import sys
from pathlib import Path

from pyspark.sql import SparkSession, functions as F, types as T

PROJECT_ROOT = Path("/Workspace/Users/thuanthongtra@gmail.com/data_expert_learning/ai_data_engineer_2026/capstone")
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from data_collection.collectors.market_document_collector import MarketDocumentCollector
from data_collection.loaders.lakebase_loader import LakebaseLoader
from real_estate_app.config import DEFAULT_DELTA_CATALOG, DEFAULT_DELTA_SCHEMA
from real_estate_app.lakebase import ensure_schema


spark = SparkSession.builder.getOrCreate()

AVAILABLE_CATALOGS = {row.catalog for row in spark.sql("SHOW CATALOGS").collect()}
RUNTIME_DELTA_CATALOG = (
    DEFAULT_DELTA_CATALOG
    if DEFAULT_DELTA_CATALOG in AVAILABLE_CATALOGS
    else spark.sql("SELECT current_catalog() AS catalog").collect()[0]["catalog"]
)
if RUNTIME_DELTA_CATALOG != DEFAULT_DELTA_CATALOG:
    print(
        f"Configured Delta catalog '{DEFAULT_DELTA_CATALOG}' is unavailable; using '{RUNTIME_DELTA_CATALOG}' instead."
    )


def _delta_name(table: str) -> str:
    return f"{RUNTIME_DELTA_CATALOG}.{DEFAULT_DELTA_SCHEMA}.{table}"


BRONZE_SCHEMA = T.StructType([
    T.StructField("id", T.StringType(), True),
    T.StructField("doc_type", T.StringType(), True),
    T.StructField("area_slug", T.StringType(), True),
    T.StructField("title", T.StringType(), True),
    T.StructField("source_url", T.StringType(), True),
    T.StructField("publisher", T.StringType(), True),
    T.StructField("published_at", T.StringType(), True),
    T.StructField("text_content", T.StringType(), True),
    T.StructField("payload", T.StringType(), True),
])


def main() -> None:
    ensure_schema()
    spark.sql(f"CREATE SCHEMA IF NOT EXISTS {RUNTIME_DELTA_CATALOG}.{DEFAULT_DELTA_SCHEMA}")
    rows = MarketDocumentCollector().collect()
    if not rows:
        print("No market documents collected.")
        return

    bronze = spark.createDataFrame(
        [
            (
                row.get("id"),
                row.get("doc_type"),
                row.get("area_slug"),
                row.get("title"),
                row.get("source_url"),
                row.get("publisher"),
                row.get("published_at"),
                row.get("text_content"),
                json.dumps(row.get("payload")) if row.get("payload") is not None else None,
            )
            for row in rows
        ],
        schema=BRONZE_SCHEMA,
    )
    bronze.write.mode("overwrite").format("delta").saveAsTable(_delta_name("bronze_market_documents"))

    silver = bronze.select(
        "id",
        "doc_type",
        "area_slug",
        "title",
        "source_url",
        "publisher",
        F.to_timestamp("published_at").alias("published_at"),
        F.trim("text_content").alias("text_content"),
        "payload",
    ).where(F.length(F.col("text_content")) > 0)

    silver.write.mode("overwrite").format("delta").saveAsTable(_delta_name("silver_market_documents"))
    spark.sql(f"ALTER TABLE {_delta_name('silver_market_documents')} SET TBLPROPERTIES (delta.enableChangeDataFeed = true)")

    clean_rows = [row.asDict() for row in silver.collect()]
    LakebaseLoader().upsert_market_documents(clean_rows)
    print(f"Upserted {len(clean_rows)} market documents via Spark bronze/silver pipeline.")


if __name__ == "__main__":
    main()