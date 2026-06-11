"""
Tool: Elastic Incident Memory
------------------------------
Pushes SENTINEL incident reports into an Elasticsearch index
(sentinel_incidents) to serve as a long-term agent memory layer.

Also exposes search_incident_history as an ADK-registered tool so
the Gemini agent can query past incidents before deciding how to patch.

Dependency: elasticsearch>=8.0.0  (optional — no-op if absent)
"""
import logging
import os
from datetime import datetime, timezone
from typing import List

logger = logging.getLogger(__name__)

INDEX_NAME = "sentinel_incidents"


def _get_client():
    """Return an Elasticsearch client or None if not configured."""
    endpoint = os.environ.get("ELASTIC_ENDPOINT")
    api_key = os.environ.get("ELASTIC_API_KEY")
    if not endpoint or not api_key:
        return None
    try:
        from elasticsearch import Elasticsearch  # type: ignore
        return Elasticsearch(endpoint, api_key=api_key)
    except ImportError:
        logger.warning(
            "[elastic] elasticsearch package not installed — "
            "run: pip install elasticsearch"
        )
        return None


def index_incident_report(report: dict) -> dict:
    """
    Indexes a completed SENTINEL incident report into Elasticsearch.
    Called automatically at the end of generate_incident_report.

    Args:
        report: The full report dict from generate_incident_report.

    Returns:
        Dict with 'indexed' bool and optional 'es_id'.
    """
    es = _get_client()
    if es is None:
        return {"indexed": False, "reason": "Elastic not configured"}

    try:
        doc = {
            **report,
            "indexed_at": datetime.now(timezone.utc).isoformat(),
        }
        resp = es.index(index=INDEX_NAME, document=doc)
        logger.info("[elastic] Incident indexed → id=%s", resp.get("_id"))
        return {"indexed": True, "es_id": resp.get("_id")}
    except Exception as exc:
        logger.error("[elastic] Failed to index incident: %s", exc)
        return {"indexed": False, "reason": str(exc)}


def search_incident_history(
    collection_name: str,
    violation_type: str = None,
    max_results: int = 5,
) -> List[dict]:
    """
    ADK Tool — Search Elastic for past incidents on a collection.

    SENTINEL calls this BEFORE patching so it can reuse a known-good
    remediation strategy instead of reasoning from scratch.

    Args:
        collection_name: MongoDB collection to search history for.
        violation_type:  Optional filter e.g. 'MISSING_REQUIRED_FIELD'.
        max_results:     Max incidents to return (default 5).

    Returns:
        List of past incident report dicts, most recent first.
        Returns empty list if Elastic is not configured.
    """
    es = _get_client()
    if es is None:
        return []

    try:
        must_clauses = [{"match": {"collection_name": collection_name}}]
        if violation_type:
            must_clauses.append({"match": {"violation_type": violation_type}})

        body = {
            "query": {"bool": {"must": must_clauses}},
            "sort": [{"timestamp": {"order": "desc"}}],
            "size": max_results,
        }
        resp = es.search(index=INDEX_NAME, body=body)
        hits = resp.get("hits", {}).get("hits", [])
        logger.info(
            "[elastic] History search for '%s' → %d hits", collection_name, len(hits)
        )
        return [h["_source"] for h in hits]
    except Exception as exc:
        logger.error("[elastic] Search failed: %s", exc)
        return []
