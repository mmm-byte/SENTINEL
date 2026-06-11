"""
Tool: generate_incident_report
--------------------------------
Synthesises the full SENTINEL 5-step pipeline run into a structured,
human-readable incident report with an executive summary and next actions.

Post-report hooks (all optional, no-op if env vars absent):
  - Elastic: indexes report into sentinel_incidents for agent memory
  - GitLab:  opens rollback MR if status=ESCALATE
"""
from datetime import datetime, timezone
import logging

logger = logging.getLogger(__name__)


def generate_incident_report(
    collection_name: str = None,
    database_name: str = None,
    violations_detected: int = None,
    documents_quarantined: int = None,
    schema_patched: bool = None,
    pipeline_trace: list = None,
    final_status: str = "CONTAINED",
) -> dict:
    """
    Generates a complete SENTINEL incident report and triggers downstream
    partner-track hooks (Elastic indexing, GitLab MR on ESCALATE).

    Args:
        collection_name:      MongoDB collection that received the corrupt payload.
        database_name:        MongoDB database name.
        violations_detected:  Total number of violations found.
        documents_quarantined: Number of documents moved to quarantine.
        schema_patched:       Whether the schema was successfully patched.
        pipeline_trace:       List of step result dicts from the pipeline.
        final_status:         "CONTAINED" | "ESCALATE" | "RESOLVED"

    Returns:
        Structured incident report dict (also pushed to Elastic).
    """
    incident_id = f"SENTINEL-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}"
    timestamp = datetime.now(timezone.utc).isoformat()

    report = {
        "incident_id": incident_id,
        "timestamp": timestamp,
        "collection_name": collection_name,
        "database_name": database_name,
        "final_status": final_status,
        "violations_detected": violations_detected,
        "documents_quarantined": documents_quarantined,
        "schema_patched": schema_patched,
        "pipeline_trace": pipeline_trace or [],
        "executive_summary": (
            f"SENTINEL ran full 5-step pipeline for collection '{collection_name}'. "
            f"Status: {final_status}. "
            f"{violations_detected or 0} violation(s) detected, "
            f"{documents_quarantined or 0} document(s) quarantined."
        ),
        "next_actions": _build_next_actions(final_status, collection_name),
    }

    # ── Track 6: Elastic — index report as agent memory ─────────────────────────
    _hook_elastic(report)

    # ── Track 5: GitLab — open MR if escalation needed ────────────────────────
    if final_status == "ESCALATE":
        _hook_gitlab(report)

    return report


# ── Post-report hooks ────────────────────────────────────────────────────────────
def _hook_elastic(report: dict) -> None:
    """Index report into Elastic — no-op if not configured."""
    try:
        from agent.tools.elastic_memory import index_incident_report  # local import avoids circular
        result = index_incident_report(report)
        if result.get("indexed"):
            logger.info("[incident_reporter] Indexed to Elastic, id=%s", result.get("es_id"))
    except Exception as exc:  # never break the pipeline
        logger.debug("[incident_reporter] Elastic hook skipped: %s", exc)


def _hook_gitlab(report: dict) -> None:
    """Open GitLab MR on ESCALATE — no-op if not configured."""
    try:
        from orchestrator.gitlab_agent import open_rollback_merge_request
        result = open_rollback_merge_request(
            violation_summary=report.get("executive_summary", ""),
            collection_name=report.get("collection_name", "unknown"),
            incident_id=report.get("incident_id", "SENTINEL-UNKNOWN"),
        )
        if result.get("created"):
            logger.info("[incident_reporter] GitLab MR created: %s", result.get("mr_url"))
            report["gitlab_mr_url"] = result.get("mr_url")
    except Exception as exc:  # never break the pipeline
        logger.debug("[incident_reporter] GitLab hook skipped: %s", exc)


def _build_next_actions(status: str, collection_name: str) -> list:
    actions = [
        f"[ ] Review quarantined documents in '{collection_name}_quarantine' and correct data.",
        "[ ] Restore strict schema validation once the producer service fix is deployed.",
        "[ ] Re-trigger Fivetran resync to align downstream warehouse with clean data.",
    ]
    if status == "ESCALATE":
        actions.insert(0,
            "⚠️ URGENT: Automated remediation incomplete — page on-call DBA. "
            "A GitLab MR has been auto-created for rollback review."
        )
    return actions


# ── Private severity helpers (kept for backward compat) ────────────────────────
def _severity(violations: list) -> str:
    if not violations:
        return "OK"
    if any(v.get("issue") == "MISSING_REQUIRED_FIELD" for v in violations):
        return "CRITICAL"
    return "WARNING"
