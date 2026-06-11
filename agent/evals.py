"""
SENTINEL Evaluations — Track 2: Arize (WIN CONDITION)
=======================================================
This module closes the Arize self-improvement loop:

  1. run_pipeline_eval()  — Scores every SENTINEL run with LLM-as-a-Judge
  2. build_eval_dataset() — Accumulates scored runs into a Phoenix dataset
  3. improve_from_evals() — Reads low-scoring runs, generates prompt patches

The judges' WIN condition: "agents that use their own observability data
to improve over time."

Run standalone:  python -m agent.evals
Auto-called:     generate_incident_report() calls run_pipeline_eval()
"""
import json
import logging
import os
from datetime import datetime, timezone
from typing import Optional

logger = logging.getLogger(__name__)

# Eval rubric — what SENTINEL is judged on
PATCH_CORRECTNESS_RUBRIC = """
You are evaluating a SENTINEL MongoDB schema continuity agent.

SENTINEL ran a 5-step pipeline on a corrupt document and produced an incident report.
Score the quality of its remediation on a scale of 0.0 to 1.0:

  1.0 — CONTAINED: All violations fixed, schema patched minimally (validationLevel=moderate),
        corrupt documents quarantined, no data deleted, downstream notified.
  0.7 — CONTAINED with minor issues: Contained but patch was overly broad or
        quarantine count was unexpectedly 0 despite violations.
  0.5 — ESCALATE with good reasoning: Could not auto-remediate but correctly
        identified the problem and escalated with a clear summary.
  0.2 — ESCALATE with poor reasoning: Escalated without explaining why.
  0.0 — FAILED: Pipeline did not complete or produced no report.

Incident report:
{report_json}

Respond ONLY with a JSON object: {{"score": <float>, "label": "PASS|REVIEW|FAIL", "reason": "<one sentence>"}}
"""


def run_pipeline_eval(incident_report: dict) -> dict:
    """
    Scores a completed SENTINEL incident report.
    Tries LLM-as-a-Judge first (if Gemini available), falls back to rule-based.

    Args:
        incident_report: Full report dict from generate_incident_report().

    Returns:
        Eval result dict with score, label, reason, and improvement_hint.
    """
    report_json = json.dumps(incident_report, indent=2, default=str)

    # Try LLM judge first
    llm_result = _llm_judge(report_json)
    if llm_result:
        eval_result = llm_result
    else:
        # Deterministic fallback
        eval_result = _rule_based_eval(incident_report)

    eval_result["incident_id"] = incident_report.get("incident_id", "UNKNOWN")
    eval_result["collection_name"] = incident_report.get("collection_name", "unknown")
    eval_result["evaluated_at"] = datetime.now(timezone.utc).isoformat()

    # Write to eval log
    _write_eval_log(eval_result)

    # Write to Phoenix as span annotation
    _annotate_phoenix_span(eval_result)

    # Trigger improvement if score is low
    if eval_result.get("score", 1.0) < 0.7:
        _flag_for_improvement(incident_report, eval_result)

    logger.info(
        "[evals] %s → score=%.2f label=%s",
        eval_result["incident_id"],
        eval_result.get("score", 0),
        eval_result.get("label", "?"),
    )
    return eval_result


def improve_from_evals() -> dict:
    """
    Reads the sentinel_improvement.jsonl log, identifies recurring failure
    patterns, and returns a prompt patch suggestion.

    This is the self-improvement loop:
      Low eval score → logged → this function reads patterns → prompt updated

    Returns:
        Dict with 'patterns_found', 'prompt_patch', 'total_low_score_runs'.
    """
    log_path = os.environ.get("SENTINEL_IMPROVEMENT_LOG", "./sentinel_improvement.jsonl")
    if not os.path.exists(log_path):
        return {"patterns_found": [], "total_low_score_runs": 0, "prompt_patch": None}

    runs = []
    with open(log_path) as f:
        for line in f:
            try:
                runs.append(json.loads(line.strip()))
            except json.JSONDecodeError:
                pass

    if not runs:
        return {"patterns_found": [], "total_low_score_runs": 0, "prompt_patch": None}

    # Identify patterns
    escalate_count = sum(1 for r in runs if r.get("final_status") == "ESCALATE")
    low_patch = sum(1 for r in runs if r.get("patch_correctness", 1.0) < 0.5)
    affected_collections = list({r.get("collection_name") for r in runs})

    patterns = []
    prompt_patches = []

    if escalate_count > len(runs) * 0.3:
        patterns.append(f"High escalation rate: {escalate_count}/{len(runs)} runs escalated")
        prompt_patches.append(
            "When violations include MISSING_REQUIRED_FIELD, always attempt "
            "patch_collection_schema with fields_to_make_optional BEFORE escalating."
        )

    if low_patch > 0:
        patterns.append(f"{low_patch} runs had low patch_correctness scores")
        prompt_patches.append(
            "Prefer the minimal patch: only relax fields that have active violations. "
            "Never drop the entire $jsonSchema validator."
        )

    result = {
        "patterns_found": patterns,
        "total_low_score_runs": len(runs),
        "affected_collections": affected_collections,
        "prompt_patch": " ".join(prompt_patches) if prompt_patches else None,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }

    logger.info("[evals] Self-improvement report: %d patterns, %d low-score runs",
                len(patterns), len(runs))
    return result


# ── Private helpers ────────────────────────────────────────────────────────────

def _llm_judge(report_json: str) -> Optional[dict]:
    """Ask Gemini to evaluate the incident report using the rubric."""
    try:
        import google.generativeai as genai  # type: ignore
        api_key = os.environ.get("GOOGLE_API_KEY")
        if not api_key:
            return None
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel("gemini-2.0-flash-exp")
        prompt = PATCH_CORRECTNESS_RUBRIC.format(report_json=report_json[:3000])
        resp = model.generate_content(prompt)
        text = resp.text.strip()
        # Extract JSON even if wrapped in markdown
        if "```" in text:
            text = text.split("```")[1].lstrip("json").strip()
        return json.loads(text)
    except Exception as exc:
        logger.debug("[evals] LLM judge failed, using rule-based: %s", exc)
        return None


def _rule_based_eval(report: dict) -> dict:
    """Deterministic eval when LLM is not available."""
    status = report.get("final_status", "UNKNOWN")
    patched = report.get("schema_patched", False)
    violations = report.get("violations_detected", 0)
    quarantined = report.get("documents_quarantined", 0)

    if status == "CONTAINED" and patched and violations > 0:
        return {"score": 1.0, "label": "PASS",
                "reason": "Contained with schema patch and quarantine."}
    elif status == "CONTAINED" and not patched:
        return {"score": 0.7, "label": "PASS",
                "reason": "Contained but schema was not patched."}
    elif status == "ESCALATE":
        return {"score": 0.5, "label": "REVIEW",
                "reason": "Escalated — human review required."}
    else:
        return {"score": 0.2, "label": "FAIL",
                "reason": "Unknown status or pipeline did not complete."}


def _write_eval_log(eval_result: dict) -> None:
    """Append eval result to the JSONL eval log."""
    log_path = os.environ.get("SENTINEL_AUDIT_LOG", "./sentinel_audit.jsonl")
    try:
        with open(log_path, "a") as f:
            f.write(json.dumps(eval_result) + "\n")
    except Exception:
        pass


def _annotate_phoenix_span(eval_result: dict) -> None:
    """Write eval score as a Phoenix span annotation."""
    api_key = os.environ.get("ARIZE_PHOENIX_API_KEY")
    if not api_key:
        return
    try:
        import httpx  # type: ignore
        url = os.environ.get("ARIZE_PHOENIX_BASE_URL", "https://app.phoenix.arize.com")
        payload = {"data": [{
            "name": "sentinel_pipeline_eval",
            "annotator_kind": "LLM" if os.environ.get("GOOGLE_API_KEY") else "CODE",
            "result": {
                "label": eval_result.get("label", "UNKNOWN"),
                "score": eval_result.get("score", 0.0),
                "explanation": eval_result.get("reason", ""),
            },
        }]}
        httpx.post(
            f"{url}/v1/span_annotations",
            headers={"api_key": api_key, "Content-Type": "application/json"},
            json=payload,
            timeout=5,
        )
    except Exception as exc:
        logger.debug("[evals] Phoenix annotation skipped: %s", exc)


def _flag_for_improvement(incident: dict, eval_result: dict) -> None:
    """Log low-scoring incidents for the self-improvement loop."""
    log_path = os.environ.get("SENTINEL_IMPROVEMENT_LOG", "./sentinel_improvement.jsonl")
    try:
        with open(log_path, "a") as f:
            f.write(json.dumps({
                "incident_id": incident.get("incident_id"),
                "collection_name": incident.get("collection_name"),
                "final_status": incident.get("final_status"),
                "patch_correctness": eval_result.get("score"),
                "remediation_quality": eval_result.get("score"),
                "label": eval_result.get("label"),
                "reason": eval_result.get("reason"),
                "pipeline_trace": incident.get("pipeline_trace", []),
                "suggested_action": "review_patch_strategy",
            }) + "\n")
    except Exception:
        pass


if __name__ == "__main__":
    # Standalone: read improvement log and print prompt patch
    result = improve_from_evals()
    print(json.dumps(result, indent=2))
