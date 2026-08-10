CREATE TABLE IF NOT EXISTS realestate.listings (
    id TEXT PRIMARY KEY,
    area_slug TEXT REFERENCES realestate.neighbourhoods(slug) ON DELETE SET NULL,
    address TEXT,
    status TEXT,
    list_price NUMERIC,
    listed_at TIMESTAMPTZ,
    source TEXT NOT NULL,
    source_url TEXT,
    payload JSONB NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_listings_area_slug ON realestate.listings (area_slug);
