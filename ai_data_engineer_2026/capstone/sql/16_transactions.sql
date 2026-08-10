CREATE TABLE IF NOT EXISTS realestate.transactions (
    id TEXT PRIMARY KEY,
    area_slug TEXT REFERENCES realestate.neighbourhoods(slug) ON DELETE SET NULL,
    address TEXT,
    sale_price NUMERIC,
    sale_date DATE,
    property_type TEXT,
    source TEXT NOT NULL,
    payload JSONB NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_transactions_area_slug ON realestate.transactions (area_slug);
