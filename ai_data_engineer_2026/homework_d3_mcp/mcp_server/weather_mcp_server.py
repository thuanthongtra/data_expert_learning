from __future__ import annotations

import logging
import os

from fastmcp import FastMCP
from sentence_transformers import SentenceTransformer

try:
    from .weather_broker import WeatherBroker
except ImportError:
    from weather_broker import WeatherBroker

try:
    from .lakebase import ensure_schema, run_query
except ImportError:
    from lakebase import ensure_schema, run_query

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("weather-mcp-server")

mcp = FastMCP("weather-prediction")
broker = WeatherBroker()

EMBEDDING_MODEL = os.environ.get("WEATHER_EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
_embedding_model: SentenceTransformer | None = None


def get_embedding_model() -> SentenceTransformer:
    global _embedding_model
    if _embedding_model is None:
        logger.info("Loading embedding model: %s", EMBEDDING_MODEL)
        _embedding_model = SentenceTransformer(EMBEDDING_MODEL)
    return _embedding_model


def _clamp_top_k(value: int | None) -> int:
    try:
        parsed = int(value) if value is not None else 5
    except Exception:
        parsed = 5
    return max(1, min(20, parsed))


@mcp.tool
def get_current_weather(location: str) -> dict:
    """
    Get the current weather for a location.

    Args:
        location: A city/state string like "Chicago, IL" or a lat/lon string like "41.8781,-87.6298".

    Returns:
        A dict containing the resolved location, current temperature, apparent temperature,
        humidity, wind speed, wind direction, weather condition, and observation time.

    Errors:
        Returns {"error": "..."} if the location cannot be resolved or the API call fails.
    """
    try:
        return broker.get_current_weather(location)
    except Exception as err:
        logger.exception("get_current_weather failed")
        return {"error": str(err)}


@mcp.tool
def get_forecast(location: str, days: int = 3) -> dict:
    """
    Get a multi-day forecast for a location.

    Args:
        location: A city/state string like "Austin, TX" or a lat/lon string like "30.2672,-97.7431".
        days: Number of forecast days to return, clamped to a safe range such as 1..7.

    Returns:
        A dict containing the resolved location and a list of daily forecast records,
        including date, high/low temperature, precipitation probability, wind speed,
        and weather condition.

    Errors:
        Returns {"error": "..."} if the location cannot be resolved or the API call fails.
    """
    try:
        return broker.get_forecast(location, days=days)
    except Exception as err:
        logger.exception("get_forecast failed")
        return {"error": str(err)}


@mcp.tool
def recommend_for_weather(location: str, date: str | None = None) -> dict:
    """
    Provide a simple weather-based recommendation.

    Args:
        location: A city/state string like "Seattle, WA" or a lat/lon string like "47.6062,-122.3321".
        date: Optional ISO date string like "2026-08-10". If omitted, use the next relevant forecast day.

    Returns:
        A dict containing a recommendation, explanation, key weather signals,
        and both Celsius/Fahrenheit plus km/h/mph values.

    Errors:
        Returns {"error": "..."} if the location cannot be resolved, the date is invalid,
        or the API call fails.
    """
    try:
        return broker.recommend_for_weather(location, target_date=date)
    except Exception as err:
        logger.exception("recommend_for_weather failed")
        return {"error": str(err)}


@mcp.tool
def compare_weather(locations: list[str]) -> dict:
    """
    Compare current weather across multiple locations.

    Args:
        locations: A list of city/state strings or lat/lon strings.

    Returns:
        A dict with one current-weather summary per resolved location.

    Errors:
        Returns {"error": "..."} if no locations are supplied or all lookups fail.
    """
    if not locations:
        return {"error": "locations is required"}

    results: list[dict] = []
    for location in locations:
        if not isinstance(location, str) or not location.strip():
            continue
        payload = get_current_weather(location)
        if "error" not in payload:
            results.append(payload)

    if not results:
        return {"error": "No locations could be resolved"}

    return {"locations": results}


@mcp.tool
def vector_search(query: str, top_k: int = 5) -> dict:
    """
    Semantic search over weather documents stored in Lakebase.

    Args:
        query: Natural language search query, e.g. "rain risk this weekend".
        top_k: Number of results to return, clamped to 1..20.

    Returns:
        A dict with query, top_k, and ranked matches joined from weather_documents and weather_embeddings.

    Errors:
        Returns {"error": "..."} if the query is missing, the tables are missing, or no data exists yet.
    """
    query = (query or "").strip()
    if not query:
        return {"error": "query is required"}

    top_k = _clamp_top_k(top_k)

    try:
        ensure_schema()
    except Exception as err:
        logger.exception("vector_search schema check failed")
        return {"error": str(err)}

    count_rows = run_query("SELECT COUNT(*) AS count FROM weather_embeddings")
    if not count_rows or int(count_rows[0]["count"]) == 0:
        return {"query": query, "top_k": top_k, "matches": [], "message": "No weather embeddings available yet"}

    query_embedding = get_embedding_model().encode(query, normalize_embeddings=True).tolist()
    rows = run_query(
        """
        WITH ranked_matches AS (
            SELECT
                d.id,
                d.location,
                d.source_type,
                d.headline,
                d.narrative_text,
                e.chunk_text,
                e.chunk_index,
                e.model_name,
                1 - (e.embedding <=> q.query_vector) AS similarity,
                ROW_NUMBER() OVER (
                    PARTITION BY d.id
                    ORDER BY e.embedding <=> q.query_vector
                ) AS doc_rank
            FROM weather_embeddings e
            JOIN weather_documents d ON d.id = e.document_id
            CROSS JOIN (SELECT %s::vector AS query_vector) q
        )
        SELECT id, location, source_type, headline, narrative_text, chunk_text, chunk_index, model_name, similarity
        FROM ranked_matches
        WHERE doc_rank = 1
        ORDER BY similarity DESC
        LIMIT %s
        """,
        (str(query_embedding), top_k),
    )

    matches: list[dict] = []
    for row in rows:
        similarity = float(row.get("similarity") or 0.0)
        matches.append({**row, "similarity_percent": round(max(0.0, min(1.0, similarity)) * 100, 2)})

    return {"query": query, "top_k": top_k, "matches": matches}


if __name__ == "__main__":
    ensure_schema()
    port = int(os.getenv("DATABRICKS_APP_PORT", os.getenv("PORT", "8000")))
    mcp.run(transport="http", host="0.0.0.0", port=port)
