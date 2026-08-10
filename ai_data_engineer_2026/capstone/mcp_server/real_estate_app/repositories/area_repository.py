from __future__ import annotations

from real_estate_app.config import table_name
from real_estate_app.lakebase import run_query, run_write, run_write_returning


def list_neighbourhoods(limit: int = 100) -> list[dict]:
    return run_query(
        f"""
        SELECT id, slug, name, display_name, city, province, country, latitude, longitude, source, updated_at
        FROM {table_name('neighbourhoods')}
        ORDER BY name ASC
        LIMIT %s
        """,
        (limit,),
    )


def get_neighbourhood_by_slug(slug: str) -> dict | None:
    rows = run_query(
        f"""
        SELECT id, slug, name, display_name, city, province, country, latitude, longitude, boundary_geojson, source, payload, updated_at
        FROM {table_name('neighbourhoods')}
        WHERE slug = %s
        """,
        (slug,),
    )
    return rows[0] if rows else None


def get_neighbourhood_by_name(name: str) -> dict | None:
    rows = run_query(
        f"""
        SELECT id, slug, name, display_name, city, province, country, latitude, longitude, boundary_geojson, source, payload, updated_at
        FROM {table_name('neighbourhoods')}
        WHERE lower(name) = lower(%s)
        """,
        (name,),
    )
    return rows[0] if rows else None


def _nearby(table: str, neighbourhood_slug: str, limit: int = 10) -> list[dict]:
    return run_query(
        f"""
        WITH n AS (
            SELECT latitude, longitude
            FROM {table_name('neighbourhoods')}
            WHERE slug = %s
        )
        SELECT a.*
        FROM {table_name(table)} a
        CROSS JOIN n
        ORDER BY ((a.latitude - n.latitude) * (a.latitude - n.latitude)) + ((a.longitude - n.longitude) * (a.longitude - n.longitude))
        LIMIT %s
        """,
        (neighbourhood_slug, limit),
    )


def get_nearby_schools(neighbourhood_slug: str, limit: int = 10) -> list[dict]:
    return _nearby("schools", neighbourhood_slug, limit)


def get_nearby_transit_stations(neighbourhood_slug: str, limit: int = 10) -> list[dict]:
    return _nearby("transit_stations", neighbourhood_slug, limit)


def get_nearby_parks(neighbourhood_slug: str, limit: int = 10) -> list[dict]:
    return _nearby("parks", neighbourhood_slug, limit)


def get_nearby_amenities(neighbourhood_slug: str, limit: int = 10) -> list[dict]:
    return _nearby("amenities", neighbourhood_slug, limit)


def get_latest_mortgage_rates(limit: int = 10) -> list[dict]:
    return run_query(
        f"""
        SELECT id, series_name, observation_date, rate_value, unit, source, updated_at
        FROM {table_name('mortgage_rates')}
        ORDER BY observation_date DESC, series_name ASC
        LIMIT %s
        """,
        (limit,),
    )


def get_demographic_snapshot(area_slug: str) -> list[dict]:
    return run_query(
        f"""
        SELECT id, area_slug, snapshot_date, metric_name, metric_value, metric_unit, source, updated_at
        FROM {table_name('demographic_snapshots')}
        WHERE area_slug = %s
        ORDER BY metric_name ASC
        """,
        (area_slug,),
    )


def get_crime_summary(area_slug: str, limit: int = 10) -> list[dict]:
    return run_query(
        f"""
        SELECT id, area_slug, event_type, occurred_at, latitude, longitude, source, updated_at
        FROM {table_name('crime_events')}
        WHERE area_slug = %s
        ORDER BY occurred_at DESC NULLS LAST, updated_at DESC
        LIMIT %s
        """,
        (area_slug, limit),
    )


def get_development_applications(area_slug: str, limit: int = 10) -> list[dict]:
    return run_query(
        f"""
        SELECT id, area_slug, title, status, address, application_type, submitted_at, latitude, longitude, source, updated_at
        FROM {table_name('development_applications')}
        WHERE area_slug = %s
        ORDER BY submitted_at DESC NULLS LAST, updated_at DESC
        LIMIT %s
        """,
        (area_slug, limit),
    )


def get_zoning_areas(area_slug: str, limit: int = 10) -> list[dict]:
    return run_query(
        f"""
        SELECT id, area_slug, zone_code, zone_label, address, latitude, longitude, source, updated_at
        FROM {table_name('zoning_areas')}
        WHERE area_slug = %s
        ORDER BY zone_code ASC, updated_at DESC
        LIMIT %s
        """,
        (area_slug, limit),
    )


def compare_areas(area_slug_a: str, area_slug_b: str) -> dict:
    area_a = get_neighbourhood_by_slug(area_slug_a)
    area_b = get_neighbourhood_by_slug(area_slug_b)
    if not area_a or not area_b:
        raise ValueError("Both area slugs must exist")
    return {
        "area_a": area_a,
        "area_b": area_b,
        "demographics_a": get_demographic_snapshot(area_slug_a),
        "demographics_b": get_demographic_snapshot(area_slug_b),
        "crime_a": get_crime_summary(area_slug_a, limit=5),
        "crime_b": get_crime_summary(area_slug_b, limit=5),
        "developments_a": get_development_applications(area_slug_a, limit=5),
        "developments_b": get_development_applications(area_slug_b, limit=5),
        "zoning_a": get_zoning_areas(area_slug_a, limit=5),
        "zoning_b": get_zoning_areas(area_slug_b, limit=5),
        "schools_a": get_nearby_schools(area_slug_a, limit=5),
        "schools_b": get_nearby_schools(area_slug_b, limit=5),
        "transit_a": get_nearby_transit_stations(area_slug_a, limit=5),
        "transit_b": get_nearby_transit_stations(area_slug_b, limit=5),
        "parks_a": get_nearby_parks(area_slug_a, limit=5),
        "parks_b": get_nearby_parks(area_slug_b, limit=5),
    }


def get_data_counts() -> dict:
    counts = {}
    for table in (
        "neighbourhoods",
        "schools",
        "transit_stations",
        "parks",
        "amenities",
        "demographic_snapshots",
        "mortgage_rates",
        "crime_events",
        "development_applications",
        "zoning_areas",
        "listings",
        "transactions",
        "market_documents",
        "market_embeddings",
        "research_notes",
        "comparison_reports",
    ):
        row = run_query(f"SELECT COUNT(*) AS count FROM {table_name(table)}")
        counts[table] = int(row[0]["count"]) if row else 0
    return counts


def get_phase_two_status() -> dict:
    return {
        "listings": {
            "status": "pending_source",
            "message": "Listings are phase 2 and require a confirmed free/legal source.",
            "row_count": get_data_counts().get("listings", 0),
        },
        "transactions": {
            "status": "pending_source",
            "message": "Transactions are phase 2 and require a confirmed free/legal source.",
            "row_count": get_data_counts().get("transactions", 0),
        },
    }


def get_analytics_metrics() -> list[dict]:
    return run_query(
        f"""
        SELECT metric_key, metric_value, metric_context, updated_at
        FROM {table_name('analytics_metrics')}
        ORDER BY metric_key ASC
        """
    )


def save_research_note(user_id: str, title: str, note_text: str, related_area_slug: str | None = None) -> dict:
    row = run_write_returning(
        f"""
        INSERT INTO {table_name('research_notes')} (user_id, title, note_text, related_area_slug)
        VALUES (%s, %s, %s, %s)
        RETURNING id, user_id, title, note_text, related_area_slug, created_at
        """,
        (user_id, title, note_text, related_area_slug),
    )
    if row is None:
        raise RuntimeError("Failed to save research note")
    return row


def create_comparison_report(user_id: str, area_slug_a: str, area_slug_b: str, prompt: str, report_text: str) -> dict:
    row = run_write_returning(
        f"""
        INSERT INTO {table_name('comparison_reports')} (user_id, area_slug_a, area_slug_b, prompt, report_text)
        VALUES (%s, %s, %s, %s, %s)
        RETURNING id, user_id, area_slug_a, area_slug_b, prompt, report_text, created_at
        """,
        (user_id, area_slug_a, area_slug_b, prompt, report_text),
    )
    if row is None:
        raise RuntimeError("Failed to create comparison report")
    return row


def save_area(user_id: str, area_slug: str) -> int:
    return run_write(
        f"""
        INSERT INTO {table_name('saved_areas')} (user_id, area_slug)
        VALUES (%s, %s)
        ON CONFLICT (user_id, area_slug) DO NOTHING
        """,
        (user_id, area_slug),
    )
