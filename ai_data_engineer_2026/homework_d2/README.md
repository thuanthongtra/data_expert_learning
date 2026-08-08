# Weather Intelligence

This project follows the Day 2 Lakebase pattern for unstructured weather text.

## Data source

National Weather Service API (`api.weather.gov`).

Why:
- free
- no API key
- rich narrative text in alerts and forecasts

## Schema

- `weather_documents`
  - raw normalized weather documents
  - `id`, `location`, `source_type`, `headline`, `narrative_text`, timestamps, `payload`
- `weather_embeddings`
  - chunked text embeddings
  - `vector(384)` using `sentence-transformers/all-MiniLM-L6-v2`

## End-to-end flow

1. `POST /weather/sync`
   - input: `{"locations": ["Chicago, IL", "Austin, TX"], "limit": 50}`
   - fetches NWS alerts/forecast text
   - upserts into `weather_documents`
2. `python notebooks/ingest_weather_embeddings.py`
   - reads unembedded docs
   - chunks long text
   - writes vectors into `weather_embeddings`
3. `POST /weather/search`
   - input: `{"query": "flash flood risk this weekend", "top_k": 5}`
   - embeds query and runs pgvector cosine search

## Notes

- Chunk size defaults to `800` with `100` overlap.
- Query results are clamped to `1..20`.
- Re-running sync is safe because `id` is stable and upserts deduplicate.
