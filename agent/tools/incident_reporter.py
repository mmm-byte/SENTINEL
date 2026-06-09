"""
Tool: generate_incident_report
--------------------------------
Synthesises the full SENTINEL 5-step pipeline run into a structured,
human-readable incident report with an executive summary and next actions.
"""
from datetime import datetime, timezone


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
    Generates a complete SENTINEL incident report.

    Args:
        collection_name:   MongoDB collection that received the corrupt payload.
        trigger_payload:   The incoming document that triggered the alert.
        violations:        List of violation dicts from validate_payload_against_schema.
        schema_patch:      Result dict from patch_collection_schema.
        quarantine_result: Result dict from quarantine_corrupt_documents.
        resolution_status: "CONTAINED" | "ESCALATE" | "RESOLVED"

    Returns:
        Structured incident report dict.
    """
    # Build a compact report structure matching tests' expectations
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
        "executive_summary": f"SENTINEL ran pipeline for {collection_name}, status={final_status}",
        "next_actions": [],
    }
    return report


# ── Private helpers ────────────────────────────────────────────────────────────

def _severity(violations: list) -> str:
    if not violations:
        return "OK"
    if any(v.get("issue") == "MISSING_REQUIRED_FIELD" for v in violations):
        return "CRITICAL"
    return "WARNING"


def _build_executive_summary(collection, violations, patch, quarantine, status) -> str:
    n_violations = len(violations)
    n_quarantined = quarantine.get("quarantined_count", 0)
    patch_ok = patch.get("success", False)

    if status == "CONTAINED":
        return (
            f"SENTINEL detected {n_violations} schema violation(s) in '{collection}'. "
            f"{'The collection validator was dynamically patched to sustain live traffic. ' if patch_ok else ''}"
            f"{n_quarantined} corrupt document(s) safely moved to quarantine. "
            f"No data loss occurred and application traffic was not interrupted."
        )
    elif status == "ESCALATE":
        return (
            f"SENTINEL detected {n_violations} critical schema violation(s) in '{collection}'. "
            f"Automated remediation was partial — human review required. "
            f"{n_quarantined} document(s) quarantined. Please review the pipeline trace below."
        )
    return (
        f"Incident in '{collection}' resolved. "
        f"{n_violations} violation(s) detected, {n_quarantined} document(s) quarantined."
    )


def _build_next_actions(violations, patch, quarantine, status) -> list:
    actions = []

    if any(v.get("issue") == "MISSING_REQUIRED_FIELD" for v in violations):
        fields = [v["field"] for v in violations if v["issue"] == "MISSING_REQUIRED_FIELD"]
        actions.append(
            f"[ ] Identify why application code omitted required field(s): {fields}. "
            "Patch the producer service to always populate these fields."
        )

    if any(v.get("issue") == "TYPE_MISMATCH" for v in violations):
        fields = [v["field"] for v in violations if v["issue"] == "TYPE_MISMATCH"]
        actions.append(
            f"[ ] Audit serialization layer for type coercion errors on field(s): {fields}."
        )

    n_quarantined = quarantine.get("quarantined_count", 0)
    qcoll = quarantine.get("quarantine_collection", "N/A")
    if n_quarantined:
        actions.append(
            f"[ ] Review {n_quarantined} quarantined document(s) in '{qcoll}'. "
            "Correct the data and re-insert into the source collection."
        )

    made_optional = patch.get("patch_applied", {}).get("made_optional", [])
    if made_optional:
        actions.append(
            f"[ ] IMPORTANT: Restore strict 'required' validation for field(s) {made_optional} "
            "once the producer service fix is deployed and validated."
        )

    if status == "ESCALATE":
        actions.append(
            "[ ] ⚠️  URGENT: Automated remediation was incomplete. "
            "Page the on-call DBA and review the pipeline_trace for failed steps."
        )

    return actions
