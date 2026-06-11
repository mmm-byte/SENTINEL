"""
Tool: generate_incident_report
--------------------------------
Synthesises the full SENTINEL 5-step pipeline run into a structured,
human-readable incident report.

Post-report hooks (all optional, no-op if env vars absent):
  Track 2 — Arize:   LLM-as-a-Judge eval + Phoenix span annotation
  Track 3 — DT:      SENTINEL span with custom attributes
  Track 6 — Elastic: Indexes report as agent memory
  Track 5 — GitLab:  Opens rollback MR if status=ESCALATE
"""
import logging
import time
from datetime import datetime, timezone

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
    partner-track hooks.

    Args:
        collection_name:      MongoDB collection that received the corrupt payload.
        database_name:        MongoDB database name.
        violations_detected:  Total violations found.
        documents_quarantined: Documents moved to quarantine.
        schema_patched:       Whether schema was successfully patched.
        pipeline_trace:       List of step result dicts.
        final_status:         "CONTAINED" | "ESCALATE" | "RESOLVED"

    Returns:
        Structured incident report dict.
    """
    incident_id = f"SENTINEL-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}"
    timestamp = datetime.now(timezone.utc).isoformat()

    report = {
        "incident_id": incident_id,
        "timestamp": timestamp,
        "collection_name": collection_name,
        "database_name": database_name,
        "final_status": final_status,
        "violations_detected": violations_detected or 0,
        "documents_quarantined": documents_quarantined or 0,
        "schema_patched": schema_patched or False,
        "pipeline_trace": pipeline_trace or [],
        "executive_summary": (
            f"SENTINEL ran full 5-step pipeline for collection '{collection_name}'. "
            f"Status: {final_status}. "
            f"{violations_detected or 0} violation(s) detected, "
            f"{documents_quarantined or 0} document(s) quarantined."
        ),
        "next_actions": _build_next_actions(final_status, collection_name),
    }

    # ── Track 3: Dynatrace — emit SENTINEL span with custom attributes ─────────
    _hook_dynatrace_span(report)

    # ── Track 6: Elastic — index report as agent memory ───────────────────────
    _hook_elastic(report)

    # ── Track 2: Arize — LLM-as-a-Judge eval + Phoenix annotation ─────────────
    _hook_arize_eval(report)

    # ── Track 5: GitLab — open rollback MR on ESCALATE ────────────────────────
    if final_status == "ESCALATE":
        _hook_gitlab(report)

    return report


# ── Post-report hooks ──────────────────────────────────────────────────────────

def _hook_dynatrace_span(report: dict) -> None:
    """Emit a SENTINEL-specific OTel span with custom attributes for Dynatrace."""
    try:
        from agent.observability import sentinel_span
        # Span has already closed by the time report is generated;
        # we annotate the current context span with report attributes.
        from opentelemetry import trace  # type: ignore
        span = trace.get_current_span()
        if span and span.is_recording():
            span.set_attribute("sentinel.incident_id", report.get("incident_id", ""))
            span.set_attribute("sentinel.collection_name", report.get("collection_name", ""))
            span.set_attribute("sentinel.violations_detected", report.get("violations_detected", 0))
            span.set_attribute("sentinel.documents_quarantined", report.get("documents_quarantined", 0))
            span.set_attribute("sentinel.schema_patched", str(report.get("schema_patched", False)))
            span.set_attribute("sentinel.resolution_status", report.get("final_status", ""))
    except Exception as exc:
        logger.debug("[dynatrace] Span annotation skipped: %s", exc)


def _hook_elastic(report: dict) -> None:
    """Index report into Elastic sentinel_incidents — no-op if not configured."""
    try:
        from agent.tools.elastic_memory import index_incident_report
        result = index_incident_report(report)
        if result.get("indexed"):
            logger.info("[elastic] Indexed to Elastic id=%s", result.get("es_id"))
    except Exception as exc:
        logger.debug("[elastic] Hook skipped: %s", exc)


def _hook_arize_eval(report: dict) -> None:
    """Run LLM-as-a-Judge eval and write score to Phoenix."""
    try:
        from agent.evals import run_pipeline_eval
        run_pipeline_eval(report)
    except Exception as exc:
        logger.debug("[arize] Eval hook skipped: %s", exc)


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
            logger.info("[gitlab] MR created: %s", result.get("mr_url"))
            report["gitlab_mr_url"] = result.get("mr_url")
    except Exception as exc:
        logger.debug("[gitlab] Hook skipped: %s", exc)


def _build_next_actions(status: str, collection_name: str) -> list:
    actions = [
        f"[ ] Review quarantined documents in '{collection_name}_quarantine' and correct data.",
        "[ ] Restore strict schema validation once the producer service fix is deployed.",
        "[ ] Re-trigger Fivetran resync to align downstream warehouse with clean data.",
        "[ ] Check Phoenix eval scores at app.phoenix.arize.com for self-improvement signals.",
    ]
    if status == "ESCALATE":
        actions.insert(0,
            "⚠️ URGENT: Automated remediation incomplete — page on-call DBA. "
            "A GitLab rollback MR has been auto-created."
        )
    return actions


def _severity(violations: list) -> str:
    if not violations:
        return "OK"
    if any(v.get("issue") == "MISSING_REQUIRED_FIELD" for v in violations):
        return "CRITICAL"
    return "WARNING"
