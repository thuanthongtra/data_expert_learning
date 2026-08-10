# Databricks notebook source
# DBTITLE 1,Cell 1
"""Spark bronze/silver pipeline for structured North York real-estate context data."""

from __future__ import annotations

import importlib
import json
import sys
from pathlib import Path

from pyspark.sql import SparkSession, functions as F, types as T

PROJECT_ROOT = Path("/Workspace/Users/thuanthongtra@gmail.com/data_expert_learning/ai_data_engineer_2026/capstone")
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import data_collection.collectors.asset_collectors as asset_collectors_module
import data_collection.collectors.boundary_collector as boundary_collector_module
import data_collection.collectors.civic_collectors as civic_collectors_module
import data_collection.collectors.demographic_collector as demographic_collector_module
import data_collection.collectors.mortgage_rate_collector as mortgage_rate_collector_module
import data_collection.collectors.neighbourhood_collector as neighbourhood_collector_module
import data_collection.loaders.lakebase_loader as lakebase_loader_module
from real_estate_app.config import DEFAULT_DELTA_CATALOG, DEFAULT_DELTA_SCHEMA
import real_estate_app.lakebase as lakebase_module

for module in (
    asset_collectors_module,
    boundary_collector_module,
    civic_collectors_module,
    demographic_collector_module,
    mortgage_rate_collector_module,
    neighbourhood_collector_module,
    lakebase_loader_module,
    lakebase_module,
):
    importlib.reload(module)

AssetCollector = asset_collectors_module.AssetCollector
BoundaryCollector = boundary_collector_module.BoundaryCollector
CivicCollectors = civic_collectors_module.CivicCollectors
DemographicCollector = demographic_collector_module.DemographicCollector
MortgageRateCollector = mortgage_rate_collector_module.MortgageRateCollector
NeighbourhoodCollector = neighbourhood_collector_module.NeighbourhoodCollector
LakebaseLoader = lakebase_loader_module.LakebaseLoader
ensure_schema = lakebase_module.ensure_schema


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


def _ensure_delta_schema() -> None:
    spark.sql(f"CREATE SCHEMA IF NOT EXISTS {RUNTIME_DELTA_CATALOG}.{DEFAULT_DELTA_SCHEMA}")


def _normalize_rows(rows: list[dict]) -> list[dict]:
    normalized_rows = []
    for row in rows:
        normalized_rows.append(
            {
                key: json.dumps(value, sort_keys=True) if isinstance(value, (dict, list)) else (None if value is None else str(value))
                for key, value in row.items()
            }
        )
    return normalized_rows


def _create_raw_df(rows: list[dict]):
    normalized_rows = _normalize_rows(rows)
    column_names = sorted({key for row in normalized_rows for key in row.keys()})
    schema = T.StructType([T.StructField(column_name, T.StringType(), True) for column_name in column_names])
    aligned_rows = [{column_name: row.get(column_name) for column_name in column_names} for row in normalized_rows]
    return spark.createDataFrame(aligned_rows, schema=schema)


def _write_bronze(table: str, rows: list[dict]) -> None:
    if not rows:
        return
    df = _create_raw_df(rows)
    df.write.mode("overwrite").format("delta").saveAsTable(_delta_name(f"bronze_{table}"))


def _silver_neighbourhoods(rows: list[dict]):
    if not rows:
        return spark.createDataFrame([], schema="id string")
    df = _create_raw_df(rows)
    return df.select(
        "id",
        "slug",
        "name",
        "display_name",
        "city",
        "province",
        "country",
        F.col("latitude").cast("double"),
        F.col("longitude").cast("double"),
        F.col("boundary_geojson").alias("boundary_geojson"),
        "source",
        F.col("payload").alias("payload"),
    )


def _silver_assets(rows: list[dict], table: str):
    if not rows:
        return spark.createDataFrame([], schema="id string")
    df = _create_raw_df(rows)
    if table == "schools":
        return df.select(
            "id", "neighbourhood_slug", "name", "school_type", "operator", "grades", "address",
            F.col("latitude").cast("double"), F.col("longitude").cast("double"), "source", F.col("payload").alias("payload")
        )
    if table == "transit_stations":
        return df.select(
            "id", "neighbourhood_slug", "name", "mode", "line_name", "address",
            F.col("latitude").cast("double"), F.col("longitude").cast("double"), "source", F.col("payload").alias("payload")
        )
    if table == "parks":
        return df.select(
            "id", "neighbourhood_slug", "name", "park_type", "address",
            F.col("latitude").cast("double"), F.col("longitude").cast("double"), "source", F.col("payload").alias("payload")
        )
    if table == "amenities":
        return df.select(
            "id", "neighbourhood_slug", "name", "amenity_type", "address",
            F.col("latitude").cast("double"), F.col("longitude").cast("double"), "source", F.col("payload").alias("payload")
        )
    if table == "mortgage_rates":
        return df.select(
            "id", "series_name", F.to_date("observation_date").alias("observation_date"), F.col("rate_value").cast("double"),
            "unit", "source", F.col("payload").alias("payload")
        )
    if table == "demographic_snapshots":
        return df.select(
            "id", "area_slug", F.to_date("snapshot_date").alias("snapshot_date"), "metric_name", F.col("metric_value").cast("double"),
            "metric_unit", "source", F.col("payload").alias("payload")
        )
    if table == "crime_events":
        return df.select(
            "id", "area_slug", "event_type", F.to_timestamp("occurred_at").alias("occurred_at"), F.col("latitude").cast("double"),
            F.col("longitude").cast("double"), "source", F.col("payload").alias("payload")
        )
    if table == "development_applications":
        return df.select(
            "id", "area_slug", "title", "status", "address", "application_type", F.to_timestamp("submitted_at").alias("submitted_at"),
            F.col("latitude").cast("double"), F.col("longitude").cast("double"), "source", F.col("payload").alias("payload")
        )
    if table == "zoning_areas":
        return df.select(
            "id", "area_slug", "zone_code", "zone_label", "address", F.col("latitude").cast("double"),
            F.col("longitude").cast("double"), "source", F.col("payload").alias("payload")
        )
    raise ValueError(f"Unsupported silver asset table: {table}")


def _enable_cdf(table: str) -> None:
    spark.sql(f"ALTER TABLE {_delta_name(table)} SET TBLPROPERTIES (delta.enableChangeDataFeed = true)")


def main() -> None:
    ensure_schema()
    _ensure_delta_schema()
    loader = LakebaseLoader()

    boundary_rows = BoundaryCollector().collect()
    neighbourhoods = NeighbourhoodCollector().collect()
    assets = AssetCollector()
    civic = CivicCollectors()

    schools = assets.collect_schools(neighbourhoods)
    transit = assets.collect_transit_stations(neighbourhoods)
    parks = assets.collect_parks(neighbourhoods)
    amenities = assets.collect_amenities(neighbourhoods)
    mortgage_rates = MortgageRateCollector().collect()
    demographic_seed = DemographicCollector().collect(neighbourhoods)
    crime_rows = civic.collect_crime_events(neighbourhoods)
    development_rows = civic.collect_development_applications(neighbourhoods)
    zoning_rows = civic.collect_zoning_areas(neighbourhoods)
    configured_demographics = civic.collect_demographic_snapshots(neighbourhoods)

    bronze_payloads = {
        "neighbourhood_boundaries": boundary_rows,
        "neighbourhoods": neighbourhoods,
        "schools": schools,
        "transit_stations": transit,
        "parks": parks,
        "amenities": amenities,
        "mortgage_rates": mortgage_rates,
        "demographic_snapshots": demographic_seed + configured_demographics,
        "crime_events": crime_rows,
        "development_applications": development_rows,
        "zoning_areas": zoning_rows,
    }
    for table, rows in bronze_payloads.items():
        _write_bronze(table, rows)

    silver_frames = {
        "silver_neighbourhoods": _silver_neighbourhoods(neighbourhoods),
        "silver_schools": _silver_assets(schools, "schools"),
        "silver_transit_stations": _silver_assets(transit, "transit_stations"),
        "silver_parks": _silver_assets(parks, "parks"),
        "silver_amenities": _silver_assets(amenities, "amenities"),
        "silver_mortgage_rates": _silver_assets(mortgage_rates, "mortgage_rates"),
        "silver_demographic_snapshots": _silver_assets(demographic_seed + configured_demographics, "demographic_snapshots"),
        "silver_crime_events": _silver_assets(crime_rows, "crime_events"),
        "silver_development_applications": _silver_assets(development_rows, "development_applications"),
        "silver_zoning_areas": _silver_assets(zoning_rows, "zoning_areas"),
    }

    silver_payload_rows = {
        "silver_neighbourhoods": neighbourhoods,
        "silver_schools": schools,
        "silver_transit_stations": transit,
        "silver_parks": parks,
        "silver_amenities": amenities,
        "silver_mortgage_rates": mortgage_rates,
        "silver_demographic_snapshots": demographic_seed + configured_demographics,
        "silver_crime_events": crime_rows,
        "silver_development_applications": development_rows,
        "silver_zoning_areas": zoning_rows,
    }

    for table, df in silver_frames.items():
        if silver_payload_rows[table]:
            df.write.mode("overwrite").format("delta").saveAsTable(_delta_name(table))
            _enable_cdf(table)

    loader.upsert_neighbourhoods(neighbourhoods)
    loader.upsert_schools(schools)
    loader.upsert_transit_stations(transit)
    loader.upsert_parks(parks)
    loader.upsert_amenities(amenities)
    loader.upsert_mortgage_rates(mortgage_rates)
    loader.upsert_demographic_snapshots(demographic_seed)
    if configured_demographics:
        loader.upsert_demographic_snapshots(configured_demographics)
    loader.upsert_crime_events(crime_rows)
    loader.upsert_development_applications(development_rows)
    loader.upsert_zoning_areas(zoning_rows)

    print("Structured Spark bronze/silver ingestion complete.")


if __name__ == "__main__":
    main()