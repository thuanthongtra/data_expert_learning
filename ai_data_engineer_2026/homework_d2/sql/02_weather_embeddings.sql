CREATE TABLE IF NOT EXISTS weather_embeddings (
    id TEXT PRIMARY KEY,
    document_id TEXT NOT NULL REFERENCES weather_documents(id) ON DELETE CASCADE,
    chunk_index INT NOT NULL,
    chunk_text TEXT NOT NULL,
    embedding VECTOR(384) NOT NULL,
    model_name TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_weather_embeddings_document_id
    ON weather_embeddings (document_id);

CREATE INDEX IF NOT EXISTS idx_weather_embeddings_embedding_hnsw
    ON weather_embeddings USING hnsw (embedding vector_cosine_ops);
