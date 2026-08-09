# Weather Pipeline Notes

## Data source choice

This project uses the National Weather Service API at `api.weather.gov` as the primary weather content source.

Why this source:

* It is free and does not require an API key.
* It provides rich narrative weather text, not just numeric conditions.
* It includes multiple content types that work well for retrieval: active alerts, grid forecasts, and area forecast discussions.
* It is a good fit for a retrieval pipeline because the narrative text contains the kind of language users ask about in natural-language search.

The implementation also uses Open-Meteo geocoding to resolve named U.S. locations such as `Seattle, WA` into coordinates before calling `api.weather.gov`. The weather source itself is still `api.weather.gov`.

## Schema decisions

### `weather_documents`

This table stores normalized source documents before embedding.

Key columns:

* `id`: stable document identifier used for upsert/deduplication
* `location`: normalized location label
* `source_type`: alert, forecast, or discussion
* `headline`: short title for display/search context
* `narrative_text`: main text body used for chunking and embeddings
* `issued_at`, `effective_at`: source timestamps when available
* `payload`: raw source JSON for traceability/debugging
* `synced_at`: sync timestamp

Why this shape:

* It separates raw source content from embedding rows.
* It keeps enough metadata to display useful search results without re-hydrating from the source API.
* `id` is the natural upsert key, so repeated syncs update existing documents instead of inserting duplicates.

### `weather_embeddings`

This table stores chunk-level embeddings for semantic search.

Key columns:

* `id`: chunk id built as `<document_id>_<chunk_index>`
* `document_id`: foreign key to `weather_documents.id`
* `chunk_index`: chunk position within the source document
* `chunk_text`: chunk content used to create the embedding
* `embedding`: pgvector `VECTOR(384)` column
* `model_name`: embedding model used
* `created_at`: embedding write timestamp

Why this shape:

* Chunk-level rows improve retrieval quality on long forecast/discussion text.
* The chunk id is deterministic, so re-embedding the same document updates the same logical rows.
* `VECTOR(384)` matches the output dimension of `sentence-transformers/all-MiniLM-L6-v2`.

### Chunking and model choices

* Embedding model: `sentence-transformers/all-MiniLM-L6-v2`
* Embedding dimension: `384`
* Default chunk size: `800` characters
* Default chunk overlap: `100` characters

Why:

* `all-MiniLM-L6-v2` is small, fast, and good enough for a lightweight retrieval demo.
* `800/100` is a simple balance between context retention and chunk count.
* Overlap helps avoid losing meaning at chunk boundaries.

## End-to-end runbook

### 1. Configure environment

Set the Lakebase connection string either in Databricks secrets or via `LAKEBASE_CONNECTION_STRING`.

For location defaults, set `WEATHER_SYNC_LOCATIONS` as a semicolon-separated list of U.S. places, for example:

`Chicago, IL;Austin, TX;New York, NY;Seattle, WA`

For manual file runs, `notebooks/ingest_weather_embeddings.py` also auto-loads missing values from `.env.example`.

### 2. Sync raw weather documents

Call `POST /weather/sync` with a JSON body such as:

`{"locations": ["Chicago, IL", "Seattle, WA"], "limit": 50}`

This step:

* resolves the location
* fetches alerts, forecasts, and discussions
* upserts rows into `weather_documents`

### 3. Build embeddings

Run [ingest_weather_embeddings.py](#file-1582279251293214).

This step:

* checks that `weather_documents` and `weather_embeddings` already exist
* fetches only documents that are not yet embedded
* bootstraps `weather_documents` from `WEATHER_SYNC_LOCATIONS` if needed
* chunks `narrative_text`
* writes/upserts chunk embeddings into `weather_embeddings`

### 4. Search

Use the app home page or call `POST /weather/search` with a JSON body such as:

`{"query": "How hot is Seattle now?", "top_k": 5}`

This step:

* embeds the query with the same sentence-transformer model
* runs pgvector cosine similarity search against `weather_embeddings`
* returns the best chunk per document so search results are deduplicated by document id

## Known limitations

* `api.weather.gov` only covers U.S. locations. A place like `North York, Ontario, Canada` is out of coverage and will not sync.
* The pipeline currently depends on external HTTP calls at sync time and initial model download time.
* Search quality is limited by a lightweight embedding model and simple character-based chunking.
* The current ingestion flow is batch-oriented, not scheduled or incremental by source change tracking.
* Manual schema creation still needs a role that owns the tables.

## Improvements with more time

* Add a Canada-capable or global weather source for non-U.S. coverage.
* Replace simple character chunking with sentence/section-aware chunking.
* Add better freshness handling so "now" questions prioritize the latest forecast periods.
* Add evaluation queries and retrieval quality checks for common weather questions.
* Turn sync + embedding into a single scheduled Lakeflow Job.
* Add observability for sync failures, skipped locations, and document/embedding counts.
