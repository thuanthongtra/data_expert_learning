CREATE TABLE IF NOT EXISTS realestate.transit_stations (
    id TEXT PRIMARY KEY,
    neighbourhood_slug TEXT REFERENCES realestate.neighbourhoods(slug) ON DELETE SET NULL,
    name TEXT NOT NULL,
    mode TEXT,
    line_name TEXT,
    address TEXT,
    latitude DOUBLE PRECISION,
    longitude DOUBLE PRECISION,
    source TEXT NOT NULL,
    payload JSONB NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_transit_neighbourhood_slug ON realestate.transit_stations (neighbourhood_slug);
