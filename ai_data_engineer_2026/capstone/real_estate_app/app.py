from __future__ import annotations

import logging
import os

from flask import Flask, jsonify, redirect, render_template, request, url_for

from data_collection.collectors.asset_collectors import AssetCollector
from data_collection.collectors.civic_collectors import CivicCollectors
from data_collection.collectors.demographic_collector import DemographicCollector
from data_collection.collectors.market_document_collector import MarketDocumentCollector
from data_collection.collectors.mortgage_rate_collector import MortgageRateCollector
from data_collection.collectors.neighbourhood_collector import NeighbourhoodCollector
from data_collection.config import configured_civic_sources, configured_market_documents
from data_collection.loaders.lakebase_loader import LakebaseLoader
from real_estate_app.lakebase import ensure_schema
from real_estate_app.repositories import area_repository, search_repository

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("real-estate-app")

app = Flask(__name__)


@app.route("/healthz")
def healthz():
    return jsonify({"status": "ok"})


@app.errorhandler(Exception)
def handle_exception(err):
    logger.exception("Unhandled exception")
    status_code = getattr(err, "code", 500)
    if not isinstance(status_code, int):
        status_code = 500
    return jsonify({"error": str(err)}), status_code


@app.route("/", methods=["GET", "POST"])
def index():
    ensure_schema()
    query = ""
    top_k = 5
    matches = []
    if request.method == "POST":
        query = (request.form.get("query") or "").strip()
        top_k = _safe_int(request.form.get("top_k"), 5)
        if query:
            matches = search_repository.vector_search(query, top_k)["matches"]
    neighbourhoods = area_repository.list_neighbourhoods(limit=25)
    return render_template(
        "index.html",
        query=query,
        top_k=top_k,
        matches=matches,
        neighbourhoods=neighbourhoods,
        sync_result=request.args.get("sync_result"),
        sync_status=area_repository.get_data_counts(),
        phase_two_status=area_repository.get_phase_two_status(),
        analytics_metrics=area_repository.get_analytics_metrics(),
        source_status={
            "civic_sources": configured_civic_sources(),
            "market_document_count": len(configured_market_documents()),
        },
    )


@app.route("/areas/<slug>")
def area_profile(slug: str):
    ensure_schema()
    area = area_repository.get_neighbourhood_by_slug(slug)
    if not area:
        return jsonify({"error": f"Unknown area slug: {slug}"}), 404
    payload = {
        "area": area,
        "schools": area_repository.get_nearby_schools(slug, limit=10),
        "transit_stations": area_repository.get_nearby_transit_stations(slug, limit=10),
        "parks": area_repository.get_nearby_parks(slug, limit=10),
        "amenities": area_repository.get_nearby_amenities(slug, limit=10),
        "demographics": area_repository.get_demographic_snapshot(slug),
        "crime": area_repository.get_crime_summary(slug, limit=10),
        "developments": area_repository.get_development_applications(slug, limit=10),
        "zoning": area_repository.get_zoning_areas(slug, limit=10),
        "mortgage_rates": area_repository.get_latest_mortgage_rates(limit=10),
    }
    if request.accept_mimetypes.best == "application/json":
        return jsonify(payload)
    return render_template("area.html", **payload)


@app.route("/compare")
def compare_page():
    ensure_schema()
    neighbourhoods = area_repository.list_neighbourhoods(limit=100)
    area_a = (request.args.get("area_a") or (neighbourhoods[0]["slug"] if neighbourhoods else "")).strip()
    area_b = (request.args.get("area_b") or (neighbourhoods[1]["slug"] if len(neighbourhoods) > 1 else area_a)).strip()
    comparison = None
    if area_a and area_b:
        try:
            comparison = area_repository.compare_areas(area_a, area_b)
        except Exception:
            comparison = None
    return render_template(
        "compare.html",
        neighbourhoods=neighbourhoods,
        area_a=area_a,
        area_b=area_b,
        comparison=comparison,
    )


@app.route("/api/compare-areas", methods=["POST"])
def api_compare_areas():
    ensure_schema()
    body = request.get_json(silent=True) or {}
    area_slug_a = (body.get("area_slug_a") or "").strip()
    area_slug_b = (body.get("area_slug_b") or "").strip()
    if not area_slug_a or not area_slug_b:
        return jsonify({"error": "area_slug_a and area_slug_b are required"}), 400
    return jsonify(area_repository.compare_areas(area_slug_a, area_slug_b))


@app.route("/api/neighbourhoods")
def api_neighbourhoods():
    ensure_schema()
    return jsonify(area_repository.list_neighbourhoods(limit=_safe_int(request.args.get("limit"), 100)))


@app.route("/api/vector-search", methods=["POST"])
def api_vector_search():
    ensure_schema()
    body = request.get_json(silent=True) or {}
    query = (body.get("query") or "").strip()
    if not query:
        return jsonify({"error": "query is required"}), 400
    top_k = _safe_int(body.get("top_k"), 5)
    return jsonify(search_repository.vector_search(query, top_k))


@app.route("/api/research-notes", methods=["POST"])
def api_research_notes():
    ensure_schema()
    body = request.get_json(silent=True) or {}
    user_id = (body.get("user_id") or "anonymous").strip()
    title = (body.get("title") or "").strip()
    note_text = (body.get("note_text") or "").strip()
    if not title or not note_text:
        return jsonify({"error": "title and note_text are required"}), 400
    row = area_repository.save_research_note(user_id, title, note_text, body.get("related_area_slug"))
    return jsonify(row)


@app.route("/api/source-status")
def api_source_status():
    return jsonify(
        {
            "civic_sources": {
                key: {"configured": bool(value), "url": value or None}
                for key, value in configured_civic_sources().items()
            },
            "market_documents": {
                "configured_count": len(configured_market_documents()),
                "sources": configured_market_documents(),
            },
        }
    )


@app.route("/api/sync-status")
def api_sync_status():
    ensure_schema()
    return jsonify(area_repository.get_data_counts())


@app.route("/api/analytics-status")
def api_analytics_status():
    ensure_schema()
    return jsonify(area_repository.get_analytics_metrics())


@app.route("/api/phase-two-status")
def api_phase_two_status():
    ensure_schema()
    return jsonify(area_repository.get_phase_two_status())


@app.route("/sync/bootstrap", methods=["POST"])
def sync_bootstrap():
    ensure_schema()
    result = run_bootstrap_sync()
    if request.accept_mimetypes.best == "application/json" or request.is_json:
        return jsonify(result)
    return redirect(url_for("index", sync_result=str(result)))


def run_bootstrap_sync() -> dict:
    loader = LakebaseLoader()

    neighbourhoods = NeighbourhoodCollector().collect()
    loader.upsert_neighbourhoods(neighbourhoods)

    asset_collector = AssetCollector()
    schools = asset_collector.collect_schools(neighbourhoods)
    transit = asset_collector.collect_transit_stations(neighbourhoods)
    parks = asset_collector.collect_parks(neighbourhoods)
    amenities = asset_collector.collect_amenities(neighbourhoods)
    loader.upsert_schools(schools)
    loader.upsert_transit_stations(transit)
    loader.upsert_parks(parks)
    loader.upsert_amenities(amenities)

    mortgage_rates = MortgageRateCollector().collect()
    loader.upsert_mortgage_rates(mortgage_rates)

    demographic_rows = DemographicCollector().collect(neighbourhoods)
    loader.upsert_demographic_snapshots(demographic_rows)

    civic_collectors = CivicCollectors()
    crime_rows = civic_collectors.collect_crime_events(neighbourhoods)
    development_rows = civic_collectors.collect_development_applications(neighbourhoods)
    zoning_rows = civic_collectors.collect_zoning_areas(neighbourhoods)
    configured_demographic_rows = civic_collectors.collect_demographic_snapshots(neighbourhoods)
    loader.upsert_crime_events(crime_rows)
    loader.upsert_development_applications(development_rows)
    loader.upsert_zoning_areas(zoning_rows)
    if configured_demographic_rows:
        loader.upsert_demographic_snapshots(configured_demographic_rows)

    documents = MarketDocumentCollector().collect()
    loader.upsert_market_documents(documents)

    return {
        "neighbourhoods": len(neighbourhoods),
        "schools": len(schools),
        "transit_stations": len(transit),
        "parks": len(parks),
        "amenities": len(amenities),
        "mortgage_rates": len(mortgage_rates),
        "demographic_snapshots": len(demographic_rows),
        "crime_events": len(crime_rows),
        "development_applications": len(development_rows),
        "zoning_areas": len(zoning_rows),
        "configured_demographic_snapshots": len(configured_demographic_rows),
        "market_documents": len(documents),
    }


def _safe_int(value, default: int) -> int:
    try:
        return int(value)
    except Exception:
        return default


if __name__ == "__main__":
    host = os.getenv("FLASK_RUN_HOST", "0.0.0.0")
    port = int(os.getenv("DATABRICKS_APP_PORT", os.getenv("FLASK_RUN_PORT", 8000)))
    debug = os.getenv("FLASK_DEBUG", "false").lower() == "true"
    app.run(debug=debug, host=host, port=port)
