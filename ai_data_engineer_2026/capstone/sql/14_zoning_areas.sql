CREATE TABLE IF NOT EXISTS realestate.zoning_areas (
    id TEXT PRIMARY KEY,
    area_slug TEXT REFERENCES realestate.neighbourhoods(slug) ON DELETE SET NULL,
    zone_code TEXT NOT NULL,
    zone_label TEXT,
    address TEXT,
    latitude DOUBLE PRECISION,
    longitude DOUBLE PRECISION,
    source TEXT NOT NULL,
    payload JSONB NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_zoning_areas_area_slug ON realestate.zoning_areas (area_slug);
