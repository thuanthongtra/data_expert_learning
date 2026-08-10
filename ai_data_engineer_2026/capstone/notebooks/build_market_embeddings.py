# Databricks notebook source
# DBTITLE 1,Install sentence-transformers
# MAGIC %pip install sentence-transformers

# COMMAND ----------

# DBTITLE 1,Cell 1
"""Spark-assisted embedding pipeline for market documents."""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

from psycopg2.extras import execute_values
from pyspark.sql import SparkSession, functions as F
from sentence_transformers import SentenceTransformer

PROJECT_ROOT = Path("/Workspace/Users/thuanthongtra@gmail.com/data_expert_learning/ai_data_engineer_2026/capstone")
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from data_collection.transformers.chunking import chunk_text
from real_estate_app.config import DEFAULT_DELTA_CATALOG, DEFAULT_DELTA_SCHEMA, DEFAULT_MODEL_NAME, table_name
from real_estate_app.lakebase import ensure_schema, get_connection, run_query


spark = SparkSession.builder.getOrCreate()

AVAILABLE_CATALOGS = {row.catalog for row in spark.sql("SHOW CATALOGS").collect()}
RUNTIME_DELTA_CATALOG = (
    DEFAULT_DELTA_CATALOG
    if DEFAULT_DELTA_CATALOG in AVAILABLE_CATALOGS
    else spark.sql("SELECT current_catalog() AS catalog").collect()[0]["catalog"]
)
if RUNTIME_DELTA_CATALOG != DEFAULT_DELTA_CATALOG:
    print(
        f"Configured Delta catalog '{DEFAULT_DELTA_CATALOG}' is unavailable; using '{RUNTIME_DELTA_CATALOG}' instead."
    )


def _delta_name(table: str) -> str:
    return f"{RUNTIME_DELTA_CATALOG}.{DEFAULT_DELTA_SCHEMA}.{table}"


def main() -> None:
    ensure_schema()
    spark.sql(f"CREATE SCHEMA IF NOT EXISTS {RUNTIME_DELTA_CATALOG}.{DEFAULT_DELTA_SCHEMA}")

    docs = run_query(
        f"""
        SELECT id, text_content
        FROM {table_name('market_documents')}
        WHERE id NOT IN (SELECT DISTINCT document_id FROM {table_name('market_embeddings')})
        ORDER BY synced_at ASC
        """
    )
    if not docs:
        print("No new market documents to embed.")
        return

    docs_df = spark.createDataFrame(docs)
    docs_df.write.mode("overwrite").format("delta").saveAsTable(_delta_name("bronze_market_embedding_source"))

    chunk_udf = F.udf(chunk_text, "array<string>")
    silver_chunks = (
        docs_df.withColumn("chunks", chunk_udf(F.col("text_content")))
        .select(
            F.col("id").alias("document_id"),
            F.posexplode_outer(F.col("chunks")).alias("chunk_index", "chunk_text"),
        )
        .where(F.col("chunk_text").isNotNull())
    )
    silver_chunks.write.mode("overwrite").format("delta").saveAsTable(_delta_name("silver_market_document_chunks"))
    spark.sql(f"ALTER TABLE {_delta_name('silver_market_document_chunks')} SET TBLPROPERTIES (delta.enableChangeDataFeed = true)")

    chunk_rows = [row.asDict() for row in silver_chunks.collect()]
    model = SentenceTransformer(os.environ.get("REAL_ESTATE_EMBEDDING_MODEL", DEFAULT_MODEL_NAME))
    rows = []
    for row in chunk_rows:
        vector = model.encode(row["chunk_text"], normalize_embeddings=True).tolist()
        rows.append(
            (
                f"{row['document_id']}_{row['chunk_index']}",
                row["document_id"],
                int(row["chunk_index"]),
                row["chunk_text"],
                json.dumps(vector),
                DEFAULT_MODEL_NAME,
                datetime.now(timezone.utc),
            )
        )

    if not rows:
        print("No embedding rows produced.")
        return

    with get_connection() as conn:
        with conn.cursor() as cur:
            execute_values(
                cur,
                f"""
                INSERT INTO {table_name('market_embeddings')} (
                    id, document_id, chunk_index, chunk_text, embedding, model_name, created_at
                ) VALUES %s
                ON CONFLICT (id) DO UPDATE
                    SET document_id = EXCLUDED.document_id,
                        chunk_index = EXCLUDED.chunk_index,
                        chunk_text = EXCLUDED.chunk_text,
                        embedding = EXCLUDED.embedding,
                        model_name = EXCLUDED.model_name,
                        created_at = EXCLUDED.created_at
                """,
                rows,
                template="(%s, %s, %s, %s, %s::vector, %s, %s)",
                page_size=100,
            )
        conn.commit()

    print(f"Upserted {len(rows)} market embeddings with Spark chunk staging.")


if __name__ == "__main__":
    main()