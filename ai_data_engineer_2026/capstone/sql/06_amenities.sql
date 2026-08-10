CREATE TABLE IF NOT EXISTS realestate.amenities (
    id TEXT PRIMARY KEY,
    neighbourhood_slug TEXT REFERENCES realestate.neighbourhoods(slug) ON DELETE SET NULL,
    name TEXT NOT NULL,
    amenity_type TEXT,
    address TEXT,
    latitude DOUBLE PRECISION,
    longitude DOUBLE PRECISION,
    source TEXT NOT NULL,
    payload JSONB NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_amenities_neighbourhood_slug ON realestate.amenities (neighbourhood_slug);
