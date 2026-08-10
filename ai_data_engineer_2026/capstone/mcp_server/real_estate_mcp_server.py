from __future__ import annotations

import logging
import os

from fastmcp import FastMCP

from brokers import document_search_broker, structured_data_broker, user_actions_broker
from lakebase import ensure_schema

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("real-estate-mcp-server")

mcp = FastMCP("north-york-real-estate")


@mcp.tool
def list_neighbourhoods(limit: int = 20) -> list[dict]:
    """
    List the known neighborhood records the system can reason about.

    Use this as a discovery tool when you need the canonical `area_slug`
    values before calling area-specific tools such as
    `get_neighbourhood_profile`, `compare_areas`, or `save_area`.

    Args:
        limit: Maximum number of neighborhoods to return.

    Returns:
        A list of neighborhood rows with identifiers such as `slug`, `name`,
        and location metadata.

    Limitations:
        Coverage is strongest for North York-focused neighborhoods that were
        explicitly ingested by the project.
    """
    return structured_data_broker.list_neighbourhoods(limit=limit)


@mcp.tool
def get_neighbourhood_profile(area_slug: str) -> dict:
    """
    Return a structured neighborhood profile for one area.

    Use this as the primary factual lookup when a user asks for an overview of
    a neighborhood or wants to evaluate one area across multiple dimensions.

    Args:
        area_slug: Canonical neighborhood identifier such as `north-york`,
            `willowdale-east`, or `bayview-village`. Call
            `list_neighbourhoods` first if you do not know the exact slug.

    Returns:
        A dictionary containing:
        - `area`: base neighborhood record
        - `schools`: nearby school records
        - `transit_stations`: nearby transit records
        - `parks`: nearby park records
        - `amenities`: nearby amenity records
        - `demographics`: demographic metrics for the area
        - `crime`: configured crime summary rows
        - `developments`: nearby development application rows
        - `zoning`: zoning rows when configured
        - `mortgage_rates`: recent mortgage-rate context

    Limitations:
        This tool does not return live listings or transactions. Some sections
        may be empty if the configured public source has no matching records.
    """
    return structured_data_broker.get_neighbourhood_profile(area_slug)


@mcp.tool
def get_schools_near_area(area_slug: str, limit: int = 10) -> list[dict]:
    """
    Return nearby schools for one neighborhood.

    Use this when the user specifically asks about schools, family context, or
    education-related amenities rather than a full area profile.

    Args:
        area_slug: Canonical neighborhood slug.
        limit: Maximum number of school rows to return.

    Returns:
        A list of school records including names, rough types, and location
        metadata when available.

    Limitations:
        "Near" is based on ingested spatial proximity, not commute analysis,
        rankings, or catchment logic.
    """
    return structured_data_broker.get_schools_near_area(area_slug, limit=limit)


@mcp.tool
def get_transit_near_area(area_slug: str, limit: int = 10) -> list[dict]:
    """
    Return nearby transit stations or stops for one neighborhood.

    Use this when the user asks about transit access, nearby stations, or
    mobility context for an area.

    Args:
        area_slug: Canonical neighborhood slug.
        limit: Maximum number of nearby transit rows to return.

    Returns:
        A list of transit records with names, mode, line/network hints, and
        location metadata.

    Limitations:
        This tool does not provide schedules, service frequency, reliability,
        or travel-time calculations.
    """
    return structured_data_broker.get_transit_near_area(area_slug, limit=limit)


@mcp.tool
def get_parks_near_area(area_slug: str, limit: int = 10) -> list[dict]:
    """
    Return nearby parks for one neighborhood.

    Use this when the user asks about green space, recreation context, or park
    availability around an area.

    Args:
        area_slug: Canonical neighborhood slug.
        limit: Maximum number of nearby park rows to return.

    Returns:
        A list of park rows with names, park types when available, and
        location metadata.

    Limitations:
        This does not score park quality or provide amenities within each park.
    """
    return structured_data_broker.get_parks_near_area(area_slug, limit=limit)


@mcp.tool
def get_amenities_near_area(area_slug: str, limit: int = 10) -> list[dict]:
    """
    Return nearby general amenities for one neighborhood.

    Use this when the user asks about convenience, daily services, or nearby
    non-park amenities without needing a full neighborhood profile.

    Args:
        area_slug: Canonical neighborhood slug.
        limit: Maximum number of amenity rows to return.

    Returns:
        A list of amenity rows such as libraries, hospitals, clinics,
        pharmacies, banks, cafes, restaurants, and community facilities when
        present in the ingested source.

    Limitations:
        Amenity categories are source-dependent and not exhaustive.
    """
    return structured_data_broker.get_amenities_near_area(area_slug, limit=limit)


@mcp.tool
def get_mortgage_rate_summary(limit: int = 10) -> list[dict]:
    """
    Return recent mortgage-rate observations used as macro pricing context.

    Use this when the user asks about rate environment, affordability context,
    or why borrowing conditions may influence real-estate comparisons.

    Args:
        limit: Maximum number of recent rate observations to return.

    Returns:
        A list of recent Bank of Canada rate observations with observation date,
        series name, and numeric rate value.

    Limitations:
        These are public rate observations, not personalized mortgage quotes or
        lender-specific offers.
    """
    return structured_data_broker.get_mortgage_rate_summary(limit=limit)


@mcp.tool
def compare_areas(area_slug_a: str, area_slug_b: str) -> dict:
    """
    Build a side-by-side factual comparison between two neighborhoods.

    Use this when the user explicitly asks to compare areas across demographics,
    crime, development activity, schools, transit, or parks.

    Args:
        area_slug_a: First canonical neighborhood slug.
        area_slug_b: Second canonical neighborhood slug.

    Returns:
        A dictionary with both base area records and paired comparison sections
        such as demographics, crime, developments, zoning, schools, transit,
        and parks.

    Limitations:
        This tool compares structured context only. Use `vector_search` if the
        user also wants narrative or document-based context.
    """
    return structured_data_broker.compare_areas(area_slug_a, area_slug_b)


@mcp.tool
def get_crime_summary(area_slug: str, limit: int = 10) -> list[dict]:
    """
    Return configured crime rows associated with one neighborhood.

    Use this when the user asks directly about safety or recent crime context
    for an area and does not need the broader profile payload.

    Args:
        area_slug: Canonical neighborhood slug.
        limit: Maximum number of crime rows to return.

    Returns:
        A list of crime-related rows with event/category labels and timestamps
        when available from the configured source.

    Limitations:
        The exact shape depends on the Toronto Open Data source configured. In
        many cases this is better interpreted as crime summary context rather
        than complete incident-level reporting.
    """
    return structured_data_broker.get_crime_summary(area_slug, limit=limit)


@mcp.tool
def get_development_applications(area_slug: str, limit: int = 10) -> list[dict]:
    """
    Return development application rows associated with one neighborhood.

    Use this when the user asks about future change, construction pipeline,
    planning pressure, or nearby development context.

    Args:
        area_slug: Canonical neighborhood slug.
        limit: Maximum number of development rows to return.

    Returns:
        A list of development application rows including title, status,
        application type, address, and submitted date when available.

    Limitations:
        Development applications indicate planning activity, not guaranteed
        project completion or delivery dates.
    """
    return structured_data_broker.get_development_applications(area_slug, limit=limit)


@mcp.tool
def get_zoning_areas(area_slug: str, limit: int = 10) -> list[dict]:
    """
    Return zoning rows associated with one neighborhood.

    Use this when the user asks about land use, zoning categories, or planning
    constraints affecting an area.

    Args:
        area_slug: Canonical neighborhood slug.
        limit: Maximum number of zoning rows to return.

    Returns:
        A list of zoning rows such as zone code, zone label, and location
        context when available.

    Limitations:
        Availability and richness depend on the configured zoning dataset. This
        tool may return sparse or empty results if no source is configured.
    """
    return structured_data_broker.get_zoning_areas(area_slug, limit=limit)


@mcp.tool
def vector_search(query: str, top_k: int = 5) -> dict:
    """
    Run semantic search over ingested market and neighborhood documents.

    Use this when the user asks a narrative, thematic, or document-driven
    question that structured tables alone do not answer well, such as market
    sentiment, neighborhood character, development concerns, or transit-related
    commentary in text sources.

    Args:
        query: Natural-language search text.
        top_k: Maximum number of matched documents to return.

    Returns:
        A dictionary containing the original query and ranked document matches
        with area slug, source URL, publisher, matched text chunk, and
        similarity score.

    Limitations:
        This searches only the ingested document corpus. It is not live web
        search. Use this together with structured tools for stronger answers.
    """
    return document_search_broker.vector_search(query, top_k)


@mcp.tool
def save_research_note(user_id: str, title: str, note_text: str, related_area_slug: str | None = None) -> dict:
    """
    Persist a research note to Lakebase.

    Use this after the user asks to save findings, a summary, or an area-specific
    note for later review.

    Args:
        user_id: Application-level user identifier.
        title: Short note title.
        note_text: Main note content to save.
        related_area_slug: Optional neighborhood slug if the note is tied to a
            specific area.

    Returns:
        The saved research-note row, including generated identifier and
        timestamp.

    Limitations:
        This only writes the provided content. It does not generate the note on
        its own.
    """
    return user_actions_broker.save_research_note(user_id, title, note_text, related_area_slug)


@mcp.tool
def save_area(user_id: str, area_slug: str) -> dict:
    """
    Save or bookmark an area for a user.

    Use this when the user asks to save an area of interest for future review.

    Args:
        user_id: Application-level user identifier.
        area_slug: Canonical neighborhood slug to save.

    Returns:
        A confirmation dictionary with the user id, area slug, and whether a new
        row was inserted.

    Limitations:
        Saving the same area again is idempotent and may report `inserted=False`.
    """
    return user_actions_broker.save_area(user_id, area_slug)


@mcp.tool
def create_comparison_report(user_id: str, area_slug_a: str, area_slug_b: str, prompt: str, report_text: str) -> dict:
    """
    Persist a finished comparison report between two areas.

    Use this after reasoning is complete and the user wants the final
    comparison saved as a durable artifact.

    Args:
        user_id: Application-level user identifier.
        area_slug_a: First area in the comparison.
        area_slug_b: Second area in the comparison.
        prompt: Original comparison request or framing prompt.
        report_text: Final comparison text to store.

    Returns:
        The saved comparison-report row, including generated identifier and
        timestamp.

    Limitations:
        This writes the supplied report only. It does not run comparison logic
        by itself; use `compare_areas` and optionally `vector_search` first.
    """
    return user_actions_broker.create_comparison_report(user_id, area_slug_a, area_slug_b, prompt, report_text)


if __name__ == "__main__":
    ensure_schema()
    port = int(os.getenv("DATABRICKS_APP_PORT", os.getenv("PORT", "8000")))
    mcp.run(transport="http", host="0.0.0.0", port=port)
