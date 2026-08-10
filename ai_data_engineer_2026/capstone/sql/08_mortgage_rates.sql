CREATE TABLE IF NOT EXISTS realestate.mortgage_rates (
    id TEXT PRIMARY KEY,
    series_name TEXT NOT NULL,
    observation_date DATE NOT NULL,
    rate_value NUMERIC NOT NULL,
    unit TEXT,
    source TEXT NOT NULL,
    payload JSONB NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_mortgage_rates_observation_date ON realestate.mortgage_rates (observation_date DESC);
