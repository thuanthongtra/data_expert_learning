# Weather Prediction MCP Server

Databricks App using FastMCP and Open-Meteo.

## Tools

- `get_current_weather(location)`
- `get_forecast(location, days)`
- `recommend_for_weather(location, date)`
- `compare_weather(locations)`
- `vector_search(query, top_k)`

## Location formats

- `Chicago, IL`
- `41.8781,-87.6298`

## Setup

1. Install dependencies from `requirements.txt`.
2. Deploy as a Databricks App using `app.yaml`.
3. Register the app URL as an external MCP server.
4. Create an Agent Bricks agent with the MCP tools enabled.
5. Run `setup_secrest.py` once to store the Lakebase connection string in the `database` secret scope.

## Lakebase

The MCP server reads from `weather_documents` and `weather_embeddings` using the same Lakebase connection-string secret pattern as Day 2.

Required secret:

- scope: `database`
- key: `lakebase_connection_string`

## Weather logic

- Open-Meteo provides current conditions and forecast data with no API key.
- The recommendation tool uses simple thresholds for umbrella/jacket/travel advice.
- `vector_search` embeds the query with `sentence-transformers/all-MiniLM-L6-v2` and searches `weather_embeddings` with pgvector cosine distance.

## Notes

- Lakebase access requires the `database/lakebase_connection_string` Databricks secret.
- The server returns clean error dictionaries instead of stack traces.
