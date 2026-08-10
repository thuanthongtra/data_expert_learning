CREATE TABLE IF NOT EXISTS realestate.demographic_snapshots (
    id TEXT PRIMARY KEY,
    area_slug TEXT REFERENCES realestate.neighbourhoods(slug) ON DELETE CASCADE,
    snapshot_date DATE NOT NULL,
    metric_name TEXT NOT NULL,
    metric_value NUMERIC,
    metric_unit TEXT,
    source TEXT NOT NULL,
    payload JSONB NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_demographic_snapshots_area_slug ON realestate.demographic_snapshots (area_slug);
