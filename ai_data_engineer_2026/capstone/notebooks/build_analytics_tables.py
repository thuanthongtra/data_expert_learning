# Databricks notebook source
# DBTITLE 1,Cell 1
"""Build Delta analytics tables, enable CDF, and sync summary metrics to Lakebase."""

from __future__ import annotations

import sys
from pathlib import Path

from pyspark.sql import SparkSession, functions as F

PROJECT_ROOT = Path("/Workspace/Users/thuanthongtra@gmail.com/data_expert_learning/ai_data_engineer_2026/capstone")
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

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


def main() -> None:
    ensure_schema()
    spark.sql(f"CREATE SCHEMA IF NOT EXISTS {RUNTIME_DELTA_CATALOG}.{DEFAULT_DELTA_SCHEMA}")

    metrics = []
    source_tables = [
        "silver_neighbourhoods",
        "silver_schools",
        "silver_transit_stations",
        "silver_parks",
        "silver_amenities",
        "silver_mortgage_rates",
        "silver_demographic_snapshots",
        "silver_crime_events",
        "silver_development_applications",
        "silver_zoning_areas",
        "silver_market_documents",
        "silver_market_document_chunks",
    ]

    for table in source_tables:
        try:
            df = spark.table(_delta_name(table))
        except Exception:
            continue
        count = df.count()
        metrics.append(
            {
                "metric_key": f"row_count_{table}",
                "metric_value": float(count),
                "metric_context": {"table": _delta_name(table), "source": "delta_silver"},
            }
        )

    if metrics:
        metrics_df = spark.createDataFrame(metrics)
        metrics_df.write.mode("overwrite").format("delta").saveAsTable(_delta_name("analytics_metrics"))
        spark.sql(f"ALTER TABLE {_delta_name('analytics_metrics')} SET TBLPROPERTIES (delta.enableChangeDataFeed = true)")

    LakebaseLoader().upsert_analytics_metrics(metrics)
    print(f"Refreshed {len(metrics)} analytics metrics.")


if __name__ == "__main__":
    main()