from __future__ import annotations

from real_estate_app.repositories import area_repository


def get_neighbourhood_profile(area_slug: str) -> dict:
    area = area_repository.get_neighbourhood_by_slug(area_slug)
    if not area:
        raise ValueError(f"Unknown neighbourhood slug: {area_slug}")
    return {
        "area": area,
        "schools": area_repository.get_nearby_schools(area_slug, limit=10),
        "transit_stations": area_repository.get_nearby_transit_stations(area_slug, limit=10),
        "parks": area_repository.get_nearby_parks(area_slug, limit=10),
        "amenities": area_repository.get_nearby_amenities(area_slug, limit=10),
        "demographics": area_repository.get_demographic_snapshot(area_slug),
        "crime": area_repository.get_crime_summary(area_slug, limit=10),
        "developments": area_repository.get_development_applications(area_slug, limit=10),
        "zoning": area_repository.get_zoning_areas(area_slug, limit=10),
        "mortgage_rates": area_repository.get_latest_mortgage_rates(limit=10),
    }


def list_neighbourhoods(limit: int = 20) -> list[dict]:
    return area_repository.list_neighbourhoods(limit=limit)


def get_schools_near_area(area_slug: str, limit: int = 10) -> list[dict]:
    return area_repository.get_nearby_schools(area_slug, limit=limit)


def get_transit_near_area(area_slug: str, limit: int = 10) -> list[dict]:
    return area_repository.get_nearby_transit_stations(area_slug, limit=limit)


def get_parks_near_area(area_slug: str, limit: int = 10) -> list[dict]:
    return area_repository.get_nearby_parks(area_slug, limit=limit)


def get_amenities_near_area(area_slug: str, limit: int = 10) -> list[dict]:
    return area_repository.get_nearby_amenities(area_slug, limit=limit)


def get_mortgage_rate_summary(limit: int = 10) -> list[dict]:
    return area_repository.get_latest_mortgage_rates(limit=limit)


def compare_areas(area_slug_a: str, area_slug_b: str) -> dict:
    return area_repository.compare_areas(area_slug_a, area_slug_b)


def get_crime_summary(area_slug: str, limit: int = 10) -> list[dict]:
    return area_repository.get_crime_summary(area_slug, limit=limit)


def get_development_applications(area_slug: str, limit: int = 10) -> list[dict]:
    return area_repository.get_development_applications(area_slug, limit=limit)


def get_zoning_areas(area_slug: str, limit: int = 10) -> list[dict]:
    return area_repository.get_zoning_areas(area_slug, limit=limit)
