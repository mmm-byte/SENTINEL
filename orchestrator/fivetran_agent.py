"""
SENTINEL Orchestrator — Fivetran Pipeline Healer
=================================================
Partner Track: Fivetran

After SENTINEL quarantines corrupt documents and the upstream schema is
healed, this agent triggers Fivetran to re-sync the downstream data
warehouse so the clean data flows through immediately.

Integration method: Fivetran REST API v1
Docs: https://fivetran.com/docs/rest-api

Env vars required:
    FIVETRAN_API_KEY     — from Fivetran → Settings → API Config
    FIVETRAN_API_SECRET  — same location
"""
import logging
import os
from typing import List

import requests

logger = logging.getLogger(__name__)

FIVETRAN_BASE = "https://api.fivetran.com/v1"


def _auth():
    """Return requests HTTPBasicAuth tuple."""
    return (
        os.environ.get("FIVETRAN_API_KEY", ""),
        os.environ.get("FIVETRAN_API_SECRET", ""),
    )


def list_fivetran_connectors() -> List[dict]:
    """
    ADK Tool — List all Fivetran connectors in the account.

    Returns a simplified list of {id, schema, status} dicts so the
    agent can identify which connector feeds the affected collection.

    Returns:
        List of connector summary dicts.
    """
    api_key, api_secret = _auth()
    if not api_key:
        logger.debug("[fivetran] FIVETRAN_API_KEY not set — skipping")
        return [{"error": "FIVETRAN_API_KEY not configured"}]

    try:
        resp = requests.get(
            f"{FIVETRAN_BASE}/connectors",
            auth=(api_key, api_secret),
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json().get("data", {}).get("items", [])
        return [
            {
                "id": c.get("id"),
                "schema": c.get("schema"),
                "status": c.get("status", {}).get("sync_state"),
                "service": c.get("service"),
            }
            for c in data
        ]
    except requests.RequestException as exc:
        logger.error("[fivetran] list_connectors failed: %s", exc)
        return [{"error": str(exc)}]


def trigger_fivetran_resync(connector_id: str) -> dict:
    """
    ADK Tool — Trigger a Fivetran connector resync.

    Called automatically after SENTINEL reports status=CONTAINED so the
    clean data propagates downstream without manual DBA intervention.

    Args:
        connector_id: The Fivetran connector ID to resync.

    Returns:
        Dict with 'triggered' bool, 'connector_id', and optional 'error'.
    """
    api_key, api_secret = _auth()
    if not api_key:
        return {"triggered": False, "connector_id": connector_id, "error": "Not configured"}

    try:
        resp = requests.post(
            f"{FIVETRAN_BASE}/connectors/{connector_id}/sync",
            auth=(api_key, api_secret),
            json={"force": True},
            timeout=10,
        )
        if resp.status_code in (200, 204):
            logger.info("[fivetran] Resync triggered for connector %s", connector_id)
            return {"triggered": True, "connector_id": connector_id, "http_status": resp.status_code}
        else:
            return {
                "triggered": False,
                "connector_id": connector_id,
                "http_status": resp.status_code,
                "error": resp.text,
            }
    except requests.RequestException as exc:
        logger.error("[fivetran] trigger_resync failed: %s", exc)
        return {"triggered": False, "connector_id": connector_id, "error": str(exc)}
