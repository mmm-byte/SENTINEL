"""
Tool: MongoDB Atlas Vector Search — Semantic Incident Recall
=============================================================
Track 1: MongoDB — WIN condition

Uses MongoDB Atlas Vector Search to find semantically similar past
incidents using Google text-embedding-004 embeddings.

This demonstrates MongoDB Atlas as the UNIFIED platform:
  - Operational data (live collections)
  - Schema validation ($jsonSchema)
  - Vector search (semantic incident memory)
  - All on a single Atlas cluster — no fragmented stack

Index required (create once via Atlas UI or mongosh):
  Collection: sentinel_incidents
  Field: embedding (2048-dim float)
  Similarity: cosine
  Index name: sentinel_vector_index
"""
import logging
import os
from typing import List

logger = logging.getLogger(__name__)


def _get_embedding(text: str) -> List[float]:
    """Generate embedding using Google text-embedding-004 via Vertex AI."""
    try:
        import vertexai  # type: ignore
        from vertexai.language_models import TextEmbeddingModel  # type: ignore

        project = os.environ.get("GOOGLE_CLOUD_PROJECT")
        location = os.environ.get("GOOGLE_CLOUD_LOCATION", "us-central1")
        vertexai.init(project=project, location=location)

        model = TextEmbeddingModel.from_pretrained("text-embedding-004")
        embeddings = model.get_embeddings([text])
        return embeddings[0].values
    except Exception as exc:
        logger.warning("[vector_search] Embedding generation failed: %s", exc)
        return []


def _get_mongo_client():
    """Return a PyMongo client or None."""
    conn = os.environ.get("MONGODB_CONNECTION_STRING")
    if not conn:
        return None, None
    try:
        from pymongo import MongoClient  # type: ignore
        client = MongoClient(conn)
        db_name = os.environ.get("MONGODB_DATABASE", "sentinel_demo")
        return client, client[db_name]
    except Exception as exc:
        logger.error("[vector_search] MongoDB connection failed: %s", exc)
        return None, None


def semantic_incident_search(
    violation_description: str,
    collection_name: str = None,
    max_results: int = 3,
) -> List[dict]:
    """
    ADK Tool — Semantic search over past SENTINEL incidents using
    MongoDB Atlas Vector Search + Google text-embedding-004.

    Finds incidents with similar violation patterns — even if the exact
    field names or error messages differ — enabling the agent to reuse
    proven remediation strategies across schema evolutions.

    Args:
        violation_description: Natural language description of the current
                               violation, e.g. 'missing required field amount
                               and type mismatch on order_id'.
        collection_name:       Optional MongoDB collection to filter by.
        max_results:           Max similar incidents to return (default 3).

    Returns:
        List of semantically similar past incident dicts, with similarity score.
        Returns empty list if Atlas Vector Search is not configured.
    """
    embedding = _get_embedding(violation_description)
    if not embedding:
        return []

    client, db = _get_mongo_client()
    if client is None:
        return []

    try:
        pipeline = [
            {
                "$vectorSearch": {
                    "index": "sentinel_vector_index",
                    "path": "embedding",
                    "queryVector": embedding,
                    "numCandidates": max_results * 10,
                    "limit": max_results,
                }
            },
            {
                "$project": {
                    "_id": 0,
                    "incident_id": 1,
                    "collection_name": 1,
                    "final_status": 1,
                    "executive_summary": 1,
                    "pipeline_trace": 1,
                    "timestamp": 1,
                    "score": {"$meta": "vectorSearchScore"},
                }
            },
        ]

        if collection_name:
            pipeline.insert(1, {"$match": {"collection_name": collection_name}})

        results = list(db["sentinel_incidents"].aggregate(pipeline))
        logger.info(
            "[vector_search] Found %d semantically similar incidents for query: '%s'",
            len(results), violation_description[:60]
        )
        return results
    except Exception as exc:
        logger.error("[vector_search] Vector search failed: %s", exc)
        return []
    finally:
        client.close()


def store_incident_with_embedding(report: dict) -> bool:
    """
    Stores a SENTINEL incident report with its vector embedding
    into MongoDB Atlas for future semantic search.

    Called automatically by generate_incident_report after each run.

    Args:
        report: Full incident report dict from generate_incident_report.

    Returns:
        True if stored successfully, False otherwise.
    """
    summary = report.get("executive_summary", "")
    if not summary:
        return False

    embedding = _get_embedding(summary)
    if not embedding:
        return False

    client, db = _get_mongo_client()
    if client is None:
        return False

    try:
        doc = {**report, "embedding": embedding}
        db["sentinel_incidents"].insert_one(doc)
        logger.info(
            "[vector_search] Incident stored with embedding: %s",
            report.get("incident_id")
        )
        return True
    except Exception as exc:
        logger.error("[vector_search] Failed to store incident with embedding: %s", exc)
        return False
    finally:
        client.close()
