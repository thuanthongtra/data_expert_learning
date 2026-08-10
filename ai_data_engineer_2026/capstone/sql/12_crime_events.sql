CREATE TABLE IF NOT EXISTS realestate.crime_events (
    id TEXT PRIMARY KEY,
    area_slug TEXT REFERENCES realestate.neighbourhoods(slug) ON DELETE SET NULL,
    event_type TEXT NOT NULL,
    occurred_at TIMESTAMPTZ,
    latitude DOUBLE PRECISION,
    longitude DOUBLE PRECISION,
    source TEXT NOT NULL,
    payload JSONB NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_crime_events_area_slug ON realestate.crime_events (area_slug);
CREATE INDEX IF NOT EXISTS idx_crime_events_occurred_at ON realestate.crime_events (occurred_at DESC);
