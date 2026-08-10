CREATE TABLE IF NOT EXISTS realestate.schools (
    id TEXT PRIMARY KEY,
    neighbourhood_slug TEXT REFERENCES realestate.neighbourhoods(slug) ON DELETE SET NULL,
    name TEXT NOT NULL,
    school_type TEXT,
    operator TEXT,
    grades TEXT,
    address TEXT,
    latitude DOUBLE PRECISION,
    longitude DOUBLE PRECISION,
    source TEXT NOT NULL,
    payload JSONB NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_schools_neighbourhood_slug ON realestate.schools (neighbourhood_slug);
