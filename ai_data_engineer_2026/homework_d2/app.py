from __future__ import annotations

import logging
import os

from flask import Flask, jsonify, render_template_string, request
from sentence_transformers import SentenceTransformer

import lakebase
from weather_client import WeatherClient

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("weather-intelligence")

app = Flask(__name__)

WEATHER_MODEL_NAME = os.environ.get("WEATHER_EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
WEATHER_TOP_K_MIN = 1
WEATHER_TOP_K_MAX = 20

HOME_PAGE_TEMPLATE = """
<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Weather Intelligence Search</title>
    <style>
      body {
        font-family: Arial, sans-serif;
        margin: 0;
        background: #f5f7fb;
        color: #1f2937;
      }
      .container {
        max-width: 960px;
        margin: 0 auto;
        padding: 32px 20px 48px;
      }
      .card {
        background: #ffffff;
        border-radius: 16px;
        padding: 24px;
        box-shadow: 0 10px 30px rgba(15, 23, 42, 0.08);
        margin-bottom: 20px;
      }
      h1, h2, h3 {
        margin-top: 0;
      }
      form {
        display: grid;
        gap: 16px;
      }
      label {
        font-weight: 600;
        display: block;
        margin-bottom: 8px;
      }
      textarea, input {
        width: 100%;
        padding: 12px;
        border: 1px solid #d1d5db;
        border-radius: 10px;
        box-sizing: border-box;
        font: inherit;
      }
      button {
        background: #2563eb;
        color: #ffffff;
        border: none;
        border-radius: 10px;
        padding: 12px 18px;
        font-weight: 600;
        cursor: pointer;
        width: fit-content;
      }
      button:hover {
        background: #1d4ed8;
      }
      .grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
        gap: 16px;
      }
      .match {
        border: 1px solid #e5e7eb;
        border-radius: 14px;
        padding: 18px;
        margin-top: 16px;
      }
      .muted {
        color: #6b7280;
      }
      .pill {
        display: inline-block;
        background: #dbeafe;
        color: #1d4ed8;
        border-radius: 999px;
        padding: 6px 12px;
        font-size: 14px;
        font-weight: 700;
        margin-bottom: 12px;
      }
      .error {
        background: #fef2f2;
        color: #b91c1c;
        border: 1px solid #fecaca;
        border-radius: 10px;
        padding: 12px 14px;
      }
      pre {
        white-space: pre-wrap;
        word-break: break-word;
        background: #f8fafc;
        border-radius: 10px;
        padding: 14px;
        margin: 12px 0 0;
      }
    </style>
  </head>
  <body>
    <div class="container">
      <div class="card">
        <h1>Weather Intelligence Search</h1>
        <p class="muted">Enter a prompt to search weather documents stored in Lakebase. Each result shows a similarity percentage based on vector search.</p>
        <form method="post" action="/">
          <div>
            <label for="query">Prompt</label>
            <textarea id="query" name="query" rows="4" placeholder="Example: heavy rain and flooding risk in Chicago this weekend">{{ query }}</textarea>
          </div>
          <div class="grid">
            <div>
              <label for="top_k">Number of results</label>
              <input id="top_k" name="top_k" type="number" min="1" max="20" value="{{ top_k }}">
            </div>
          </div>
          <button type="submit">Search weather knowledge</button>
        </form>
      </div>

      {% if error %}
      <div class="card error">{{ error }}</div>
      {% endif %}

      {% if message and not matches %}
      <div class="card">
        <p>{{ message }}</p>
      </div>
      {% endif %}

      {% if matches %}
      <div class="card">
        <h2>Results for "{{ query }}"</h2>
        <p class="muted">Showing top {{ matches|length }} matches.</p>
        {% for match in matches %}
        <div class="match">
          <div class="pill">{{ match.similarity_percent }}% match</div>
          <h3>{{ match.headline }}</h3>
          <p><strong>Location:</strong> {{ match.location }}</p>
          <p><strong>Document ID:</strong> {{ match.id }}</p>
          <p><strong>Chunk:</strong></p>
          <pre>{{ match.chunk_text }}</pre>
          <p><strong>Narrative:</strong></p>
          <pre>{{ match.narrative_text }}</pre>
        </div>
        {% endfor %}
      </div>
      {% endif %}
    </div>
  </body>
</html>
"""

_embedding_model: SentenceTransformer | None = None


def get_embedding_model() -> SentenceTransformer:
    global _embedding_model
    if _embedding_model is None:
        _embedding_model = SentenceTransformer(WEATHER_MODEL_NAME)
    return _embedding_model


def _embed_text(text: str) -> list[float]:
    return get_embedding_model().encode(text, normalize_embeddings=True).tolist()


def _clamp_top_k(value: int | None) -> int:
    if value is None:
        return 5
    return max(WEATHER_TOP_K_MIN, min(WEATHER_TOP_K_MAX, value))


@app.route("/", methods=["GET", "POST"])
def index():
    query = ""
    top_k = 5
    matches: list[dict] = []
    error = None
    message = None

    if request.method == "POST":
        query = (request.form.get("query") or "").strip()
        top_k = _clamp_top_k(_safe_int(request.form.get("top_k"), 5))

        if not query:
            error = "Prompt is required"
        else:
            payload = _search_weather_matches(query, top_k)
            matches = payload["matches"]
            message = payload.get("message")

    return render_template_string(
        HOME_PAGE_TEMPLATE,
        query=query,
        top_k=top_k,
        matches=matches,
        error=error,
        message=message,
    )


@app.route("/api")
def api_index():
    return jsonify(
        {
            "app": "ai-data-engineer-hw-d2",
            "status": "ok",
            "message": "Weather Intelligence API is running",
            "endpoints": {
                "home": {"method": "GET", "path": "/"},
                "healthz": {"method": "GET", "path": "/healthz"},
                "sync_weather": {"method": "POST", "path": "/weather/sync"},
                "search_weather": {"method": "POST", "path": "/weather/search"},
            },
        }
    )


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


@app.route("/weather/sync", methods=["POST"])
def sync_weather():
    lakebase.ensure_schema()
    body = request.get_json(silent=True) or {}
    locations = body.get("locations") or []
    limit = max(1, _safe_int(body.get("limit"), 50))

    if not isinstance(locations, list) or not locations:
        return jsonify({"error": "locations must be a non-empty list"}), 400

    client = WeatherClient()
    synced = 0
    for location in locations:
        if not isinstance(location, str) or not location.strip():
            continue
        docs = client.fetch_documents(location, limit=limit)
        synced += _upsert_documents(docs)

    return jsonify({"synced": synced, "locations": locations})


@app.route("/weather/search", methods=["POST"])
def search_weather():
    body = request.get_json(silent=True) or {}
    query = (body.get("query") or "").strip()
    top_k = _clamp_top_k(_safe_int(body.get("top_k"), 5))

    if not query:
        return jsonify({"error": "query is required"}), 400

    return jsonify(_search_weather_matches(query, top_k))


def _require_weather_tables() -> None:
    rows = lakebase.run_query(
        """
        SELECT
            to_regclass('public.weather_documents') AS weather_documents,
            to_regclass('public.weather_embeddings') AS weather_embeddings
        """
    )
    row = rows[0] if rows else {}
    missing = [
        table_name
        for table_name in ("weather_documents", "weather_embeddings")
        if not row.get(table_name)
    ]
    if missing:
        raise RuntimeError(
            f"Missing required table(s): {', '.join(missing)}. Create them with a role that owns the tables before using search."
        )



def _search_weather_matches(query: str, top_k: int) -> dict:
    _require_weather_tables()

    count_rows = lakebase.run_query("SELECT COUNT(*) AS count FROM weather_embeddings")
    if not count_rows or int(count_rows[0]["count"]) == 0:
        return {"query": query, "top_k": top_k, "matches": [], "message": "No weather embeddings available yet"}

    query_embedding = _embed_text(query)
    rows = lakebase.run_query(
        """
        WITH ranked_matches AS (
            SELECT d.id, d.location, d.headline, d.narrative_text, e.chunk_text,
                   1 - (e.embedding <=> q.query_vector) AS similarity,
                   ROW_NUMBER() OVER (
                       PARTITION BY d.id
                       ORDER BY e.embedding <=> q.query_vector
                   ) AS doc_rank
            FROM weather_embeddings e
            JOIN weather_documents d ON d.id = e.document_id
            CROSS JOIN (SELECT %s::vector AS query_vector) q
        )
        SELECT id, location, headline, narrative_text, chunk_text, similarity
        FROM ranked_matches
        WHERE doc_rank = 1
        ORDER BY similarity DESC
        LIMIT %s
        """,
        (query_embedding, top_k),
    )
    matches = []
    for row in rows:
        similarity = float(row.get("similarity") or 0.0)
        similarity_percent = round(max(0.0, min(1.0, similarity)) * 100, 2)
        matches.append(
            {
                **row,
                "similarity_percent": similarity_percent,
            }
        )

    return {"query": query, "top_k": top_k, "matches": matches}


def _safe_int(value, default: int) -> int:
    try:
        return int(value)
    except Exception:
        return default


def _upsert_documents(docs: list) -> int:
    if not docs:
        return 0

    import json as _json

    count = 0
    with lakebase.get_connection() as conn:
        with conn.cursor() as cur:
            for doc in docs:
                cur.execute(
                    """
                    INSERT INTO weather_documents (
                        id, location, source_type, headline, narrative_text,
                        issued_at, effective_at, payload, synced_at
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, now())
                    ON CONFLICT (id) DO UPDATE
                        SET location = EXCLUDED.location,
                            source_type = EXCLUDED.source_type,
                            headline = EXCLUDED.headline,
                            narrative_text = EXCLUDED.narrative_text,
                            issued_at = EXCLUDED.issued_at,
                            effective_at = EXCLUDED.effective_at,
                            payload = EXCLUDED.payload,
                            synced_at = EXCLUDED.synced_at
                    """,
                    (
                        doc.id,
                        doc.location,
                        doc.source_type,
                        doc.headline,
                        doc.narrative_text,
                        doc.issued_at,
                        doc.effective_at,
                        _json.dumps(doc.payload),
                    ),
                )
                count += 1
            conn.commit()
    return count


if __name__ == "__main__":
    host = os.getenv("FLASK_RUN_HOST", "0.0.0.0")
    port = int(os.getenv("DATABRICKS_APP_PORT", os.getenv("FLASK_RUN_PORT", 8000)))
    debug = os.getenv("FLASK_DEBUG", "false").lower() == "true"
    app.run(debug=debug, host=host, port=port)
