from __future__ import annotations

import json

from real_estate_app.config import table_name
from real_estate_app.lakebase import get_connection


class LakebaseLoader:
    def upsert_neighbourhoods(self, rows: list[dict]) -> int:
        return self._write_many(
            f"""
            INSERT INTO {table_name('neighbourhoods')} (
                id, slug, name, display_name, city, province, country,
                latitude, longitude, boundary_geojson, source, payload, updated_at
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, now())
            ON CONFLICT (id) DO UPDATE
                SET slug = EXCLUDED.slug,
                    name = EXCLUDED.name,
                    display_name = EXCLUDED.display_name,
                    city = EXCLUDED.city,
                    province = EXCLUDED.province,
                    country = EXCLUDED.country,
                    latitude = EXCLUDED.latitude,
                    longitude = EXCLUDED.longitude,
                    boundary_geojson = EXCLUDED.boundary_geojson,
                    source = EXCLUDED.source,
                    payload = EXCLUDED.payload,
                    updated_at = EXCLUDED.updated_at
            """,
            [
                (
                    row["id"], row["slug"], row["name"], row["display_name"], row["city"], row["province"],
                    row["country"], row["latitude"], row["longitude"], json.dumps(row["boundary_geojson"]) if row.get("boundary_geojson") else None,
                    row["source"], json.dumps(row["payload"])
                )
                for row in rows
            ],
        )

    def upsert_schools(self, rows: list[dict]) -> int:
        return self._upsert_asset_table("schools", rows, [
            "id", "neighbourhood_slug", "name", "school_type", "operator", "grades", "address", "latitude", "longitude", "source", "payload"
        ])

    def upsert_transit_stations(self, rows: list[dict]) -> int:
        return self._upsert_asset_table("transit_stations", rows, [
            "id", "neighbourhood_slug", "name", "mode", "line_name", "address", "latitude", "longitude", "source", "payload"
        ])

    def upsert_parks(self, rows: list[dict]) -> int:
        return self._upsert_asset_table("parks", rows, [
            "id", "neighbourhood_slug", "name", "park_type", "address", "latitude", "longitude", "source", "payload"
        ])

    def upsert_amenities(self, rows: list[dict]) -> int:
        return self._upsert_asset_table("amenities", rows, [
            "id", "neighbourhood_slug", "name", "amenity_type", "address", "latitude", "longitude", "source", "payload"
        ])

    def upsert_mortgage_rates(self, rows: list[dict]) -> int:
        return self._write_many(
            f"""
            INSERT INTO {table_name('mortgage_rates')} (
                id, series_name, observation_date, rate_value, unit, source, payload, updated_at
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, now())
            ON CONFLICT (id) DO UPDATE
                SET series_name = EXCLUDED.series_name,
                    observation_date = EXCLUDED.observation_date,
                    rate_value = EXCLUDED.rate_value,
                    unit = EXCLUDED.unit,
                    source = EXCLUDED.source,
                    payload = EXCLUDED.payload,
                    updated_at = EXCLUDED.updated_at
            """,
            [
                (
                    row["id"], row["series_name"], row["observation_date"], row["rate_value"], row["unit"], row["source"], json.dumps(row["payload"])
                )
                for row in rows
            ],
        )

    def upsert_demographic_snapshots(self, rows: list[dict]) -> int:
        return self._write_many(
            f"""
            INSERT INTO {table_name('demographic_snapshots')} (
                id, area_slug, snapshot_date, metric_name, metric_value, metric_unit, source, payload, updated_at
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, now())
            ON CONFLICT (id) DO UPDATE
                SET area_slug = EXCLUDED.area_slug,
                    snapshot_date = EXCLUDED.snapshot_date,
                    metric_name = EXCLUDED.metric_name,
                    metric_value = EXCLUDED.metric_value,
                    metric_unit = EXCLUDED.metric_unit,
                    source = EXCLUDED.source,
                    payload = EXCLUDED.payload,
                    updated_at = EXCLUDED.updated_at
            """,
            [
                (
                    row["id"], row["area_slug"], row["snapshot_date"], row["metric_name"], row["metric_value"], row["metric_unit"], row["source"], json.dumps(row["payload"])
                )
                for row in rows
            ],
        )

    def upsert_market_documents(self, rows: list[dict]) -> int:
        return self._write_many(
            f"""
            INSERT INTO {table_name('market_documents')} (
                id, doc_type, area_slug, title, source_url, publisher, published_at, text_content, payload, synced_at
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, now())
            ON CONFLICT (id) DO UPDATE
                SET doc_type = EXCLUDED.doc_type,
                    area_slug = EXCLUDED.area_slug,
                    title = EXCLUDED.title,
                    source_url = EXCLUDED.source_url,
                    publisher = EXCLUDED.publisher,
                    published_at = EXCLUDED.published_at,
                    text_content = EXCLUDED.text_content,
                    payload = EXCLUDED.payload,
                    synced_at = EXCLUDED.synced_at
            """,
            [
                (
                    row["id"], row["doc_type"], row.get("area_slug"), row["title"], row["source_url"], row.get("publisher"),
                    row.get("published_at"), row["text_content"], json.dumps(row["payload"])
                )
                for row in rows
            ],
        )

    def upsert_crime_events(self, rows: list[dict]) -> int:
        return self._write_many(
            f"""
            INSERT INTO {table_name('crime_events')} (
                id, area_slug, event_type, occurred_at, latitude, longitude, source, payload, updated_at
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, now())
            ON CONFLICT (id) DO UPDATE
                SET area_slug = EXCLUDED.area_slug,
                    event_type = EXCLUDED.event_type,
                    occurred_at = EXCLUDED.occurred_at,
                    latitude = EXCLUDED.latitude,
                    longitude = EXCLUDED.longitude,
                    source = EXCLUDED.source,
                    payload = EXCLUDED.payload,
                    updated_at = EXCLUDED.updated_at
            """,
            [
                (
                    row["id"], row["area_slug"], row["event_type"], row.get("occurred_at"), row.get("latitude"), row.get("longitude"), row["source"], json.dumps(row["payload"])
                )
                for row in rows
            ],
        )

    def upsert_development_applications(self, rows: list[dict]) -> int:
        return self._write_many(
            f"""
            INSERT INTO {table_name('development_applications')} (
                id, area_slug, title, status, address, application_type, submitted_at, latitude, longitude, source, payload, updated_at
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, now())
            ON CONFLICT (id) DO UPDATE
                SET area_slug = EXCLUDED.area_slug,
                    title = EXCLUDED.title,
                    status = EXCLUDED.status,
                    address = EXCLUDED.address,
                    application_type = EXCLUDED.application_type,
                    submitted_at = EXCLUDED.submitted_at,
                    latitude = EXCLUDED.latitude,
                    longitude = EXCLUDED.longitude,
                    source = EXCLUDED.source,
                    payload = EXCLUDED.payload,
                    updated_at = EXCLUDED.updated_at
            """,
            [
                (
                    row["id"], row["area_slug"], row["title"], row.get("status"), row.get("address"), row.get("application_type"), row.get("submitted_at"), row.get("latitude"), row.get("longitude"), row["source"], json.dumps(row["payload"])
                )
                for row in rows
            ],
        )

    def upsert_zoning_areas(self, rows: list[dict]) -> int:
        return self._write_many(
            f"""
            INSERT INTO {table_name('zoning_areas')} (
                id, area_slug, zone_code, zone_label, address, latitude, longitude, source, payload, updated_at
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, now())
            ON CONFLICT (id) DO UPDATE
                SET area_slug = EXCLUDED.area_slug,
                    zone_code = EXCLUDED.zone_code,
                    zone_label = EXCLUDED.zone_label,
                    address = EXCLUDED.address,
                    latitude = EXCLUDED.latitude,
                    longitude = EXCLUDED.longitude,
                    source = EXCLUDED.source,
                    payload = EXCLUDED.payload,
                    updated_at = EXCLUDED.updated_at
            """,
            [
                (
                    row["id"], row["area_slug"], row["zone_code"], row.get("zone_label"), row.get("address"), row.get("latitude"), row.get("longitude"), row["source"], json.dumps(row["payload"])
                )
                for row in rows
            ],
        )

    def upsert_analytics_metrics(self, rows: list[dict]) -> int:
        return self._write_many(
            f"""
            INSERT INTO {table_name('analytics_metrics')} (
                metric_key, metric_value, metric_context, updated_at
            ) VALUES (%s, %s, %s, now())
            ON CONFLICT (metric_key) DO UPDATE
                SET metric_value = EXCLUDED.metric_value,
                    metric_context = EXCLUDED.metric_context,
                    updated_at = EXCLUDED.updated_at
            """,
            [
                (row["metric_key"], row.get("metric_value"), json.dumps(row.get("metric_context") or {}))
                for row in rows
            ],
        )

    def _upsert_asset_table(self, table: str, rows: list[dict], columns: list[str]) -> int:
        if not rows:
            return 0
        insert_columns = ", ".join(columns + ["updated_at"])
        placeholders = ", ".join(["%s"] * len(columns) + ["now()"])
        updates = ",\n                    ".join(
            f"{column} = EXCLUDED.{column}" for column in columns if column != "id"
        )
        sql = f"""
            INSERT INTO {table_name(table)} ({insert_columns})
            VALUES ({placeholders})
            ON CONFLICT (id) DO UPDATE
                SET {updates},
                    updated_at = EXCLUDED.updated_at
        """
        values = [
            tuple(json.dumps(row[column]) if column == "payload" else row.get(column) for column in columns)
            for row in rows
        ]
        return self._write_many(sql, values)

    def _write_many(self, sql: str, values: list[tuple]) -> int:
        if not values:
            return 0
        count = 0
        with get_connection() as conn:
            with conn.cursor() as cur:
                for value in values:
                    cur.execute(sql, value)
                    count += 1
                conn.commit()
        return count
