CREATE TABLE IF NOT EXISTS realestate.development_applications (
    id TEXT PRIMARY KEY,
    area_slug TEXT REFERENCES realestate.neighbourhoods(slug) ON DELETE SET NULL,
    title TEXT NOT NULL,
    status TEXT,
    address TEXT,
    application_type TEXT,
    submitted_at TIMESTAMPTZ,
    latitude DOUBLE PRECISION,
    longitude DOUBLE PRECISION,
    source TEXT NOT NULL,
    payload JSONB NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_development_applications_area_slug ON realestate.development_applications (area_slug);
