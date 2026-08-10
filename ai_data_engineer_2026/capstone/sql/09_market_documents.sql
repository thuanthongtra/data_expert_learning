CREATE TABLE IF NOT EXISTS realestate.market_documents (
    id TEXT PRIMARY KEY,
    doc_type TEXT NOT NULL,
    area_slug TEXT,
    title TEXT NOT NULL,
    source_url TEXT NOT NULL,
    publisher TEXT,
    published_at TIMESTAMPTZ,
    text_content TEXT NOT NULL,
    payload JSONB NOT NULL,
    synced_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_market_documents_area_slug ON realestate.market_documents (area_slug);
