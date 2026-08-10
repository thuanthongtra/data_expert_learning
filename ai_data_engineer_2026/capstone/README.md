# North York Real Estate Copilot

Databricks-oriented capstone project for researching real estate in Ontario with an initial focus on North York.

## Project Layout

- `real_estate_app/`: Flask app, query layer, and UI
- `data_collection/`: API clients, collectors, transformers, and loaders
- `notebooks/`: Databricks-friendly ingestion and embedding jobs
- `mcp_server/`: FastMCP server exposing read/write real-estate tools
- `agent/`: Databricks agent skeleton and prompt
- `sql/`: Lakebase DDL for the `realestate` schema
- `resources/`: job configuration placeholders

## Current Capabilities

- bootstrap North York neighborhood context data
- collect nearby schools, transit, parks, and amenities
- collect mortgage rate observations from Bank of Canada
- ingest curated market/neighborhood documents from the web
- build pgvector embeddings in `realestate.market_embeddings`
- expose a Flask app for search, area profiles, comparison, and manual sync
- expose an MCP server over the same Lakebase-backed data
- support Toronto Open Data dataset pages directly when they expose CSV/GeoJSON/JSON download links
- top-level Databricks bundle config for the Flask UI, MCP server, and jobs
- Spark-oriented bronze/silver Delta notebooks plus CDF-driven analytics refresh

## Real Toronto Civic Sources

The code is ready to accept real public dataset URLs through environment variables.

- `TORONTO_CRIME_SOURCE_URL`
- `TORONTO_DEVELOPMENT_SOURCE_URL`
- `TORONTO_ZONING_SOURCE_URL`
- `TORONTO_DEMOGRAPHICS_SOURCE_URL`
- `TORONTO_NEIGHBOURHOOD_BOUNDARIES_SOURCE_URL`

Each source can point to a public JSON, GeoJSON, or CSV URL. The civic collectors normalize rows into the `realestate` schema without changing the app or MCP surface.
The loader also supports Toronto Open Data dataset pages directly and will attempt to discover a downloadable resource link automatically.

Recommended starting values:

- `TORONTO_NEIGHBOURHOOD_BOUNDARIES_SOURCE_URL=https://open.toronto.ca/dataset/neighbourhood-boundaries/`
- `TORONTO_CRIME_SOURCE_URL=https://open.toronto.ca/dataset/neighbourhood-crime-rates/`
- `TORONTO_DEVELOPMENT_SOURCE_URL=https://open.toronto.ca/dataset/development-applications/`
- `TORONTO_DEMOGRAPHICS_SOURCE_URL=https://open.toronto.ca/dataset/neighbourhood-profiles/`

## Market Document Source Configuration

By default, the project uses a small curated set of neighborhood documents.

To override them without code changes, set `REAL_ESTATE_MARKET_DOCUMENTS_JSON` to a JSON array such as:

```json
[
  {
    "doc_type": "market_news",
    "area_slug": "north-york",
    "publisher": "Example Publisher",
    "source_url": "https://example.com/article"
  }
]
```

## Useful Endpoints

- `POST /sync/bootstrap`: run the first-slice collectors
- `GET /api/source-status`: inspect configured civic/document sources
- `GET /api/sync-status`: inspect current row counts in Lakebase
- `GET /api/phase-two-status`: inspect listings/transactions phase-2 placeholders
- `GET /api/analytics-status`: inspect Delta/CDF-derived analytics metrics synced into Lakebase
- `POST /api/vector-search`: semantic search over ingested documents
- `POST /api/compare-areas`: compare two neighborhoods

## First Slice

This repository implements the first working slice:

- curated North York neighborhoods
- nearby schools, transit, parks, and amenities via OpenStreetMap/Overpass
- mortgage rate ingestion via Bank of Canada Valet API
- market and neighborhood document ingestion from curated web sources
- chunk embeddings in Lakebase with pgvector
- Flask UI and API endpoints
- MCP tools over the same data

## Phase 2 Placeholders

`listings` and `transactions` schema support is included, but live ingestion is intentionally not implemented until a confirmed free/legal source is selected.

## Spark + Delta + CDF

The Databricks notebooks now implement a Spark-oriented pattern:

- ingest source data into Delta bronze tables
- normalize into Delta silver tables
- enable Change Data Feed on the silver tables
- refresh Lakebase serving tables from the silver outputs
- aggregate CDF-driven analytics into Lakebase `analytics_metrics`

## Environment

Copy `.env.example` to `.env` and fill in the Lakebase connection string if you want to run locally without Databricks secrets.
