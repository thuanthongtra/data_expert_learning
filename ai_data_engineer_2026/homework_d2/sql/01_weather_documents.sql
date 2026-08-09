CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS weather_documents (
    id TEXT PRIMARY KEY,
    location TEXT NOT NULL,
    source_type TEXT NOT NULL,
    headline TEXT NOT NULL,
    narrative_text TEXT NOT NULL,
    issued_at TIMESTAMPTZ,
    effective_at TIMESTAMPTZ,
    payload JSONB NOT NULL,
    synced_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_weather_documents_location
    ON weather_documents (location);
