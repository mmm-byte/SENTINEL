"""
SENTINEL — Arize Phoenix Self-Improvement Loop
===============================================
Track 2: Arize — WIN condition

This module:
  1. Pulls recent SENTINEL traces from Phoenix via REST API
  2. Runs LLM-as-a-Judge evaluation on each trace:
     - Was the patch strategy minimally invasive?
     - Did the agent correctly classify all violation types?
     - Was the quarantine decision correct?
  3. Writes eval scores back to Phoenix as a labeled dataset
  4. Generates a system-prompt improvement recommendation
     based on patterns in low-scoring traces

Call run_self_improvement_loop() after every 10 incidents
or on a schedule (e.g. daily cron via Cloud Scheduler).
"""
import json
import logging
import os
from datetime import datetime, timezone
from typing import List

logger = logging.getLogger(__name__)


# ── Judge prompt ───────────────────────────────────────────────────────────────
JUDGE_SYSTEM_PROMPT = """
You are an expert MongoDB database engineer and AI agent evaluator.
You will be given a SENTINEL incident trace — the full sequence of tool
calls and outputs from an autonomous schema-healing agent.

Score the agent's performance on three dimensions (0.0 to 1.0 each):

1. patch_minimality: Did the agent make the LEAST invasive patch possible?
   (e.g. making one field optional is better than dropping the whole validator)
   1.0 = perfectly minimal, 0.0 = unnecessarily destructive patch

2. violation_accuracy: Did the agent correctly identify ALL violations and
   ONLY real violations? No false positives, no missed violations.
   1.0 = perfect classification, 0.0 = missed or hallucinated violations

3. quarantine_correctness: Did the agent quarantine the right documents?
   Should only quarantine truly corrupt docs, not valid ones.
   1.0 = correct quarantine, 0.0 = wrong docs quarantined

Return ONLY valid JSON:
{
  "patch_minimality": <float>,
  "violation_accuracy": <float>,
  "quarantine_correctness": <float>,
  "overall": <float>,
  "reasoning": "<one sentence>",
  "improvement_hint": "<one actionable suggestion for the agent>"
}
"""


def run_self_improvement_loop(last_n_traces: int = 10) -> dict:
    """
    WIN condition for Arize track:
    Pulls traces → evaluates → writes scores back → returns improvement hints.

    Args:
        last_n_traces: Number of recent traces to evaluate.

    Returns:
        Dict with eval_scores list, avg_scores, and improvement_recommendations.
    """
    api_key = os.environ.get("ARIZE_PHOENIX_API_KEY")
    if not api_key:
        logger.debug("[evals] ARIZE_PHOENIX_API_KEY not set — skipping eval loop")
        return {"skipped": True, "reason": "Arize not configured"}

    traces = _fetch_recent_traces(api_key, last_n_traces)
    if not traces:
        return {"skipped": True, "reason": "No traces found"}

    eval_results = []
    improvement_hints = []

    for trace in traces:
        score = _judge_trace(trace)
        eval_results.append(score)
        if score.get("overall", 1.0) < 0.75:
            improvement_hints.append(score.get("improvement_hint", ""))

    # Write scores back to Phoenix
    _write_evals_to_phoenix(api_key, eval_results)

    # Aggregate
    if eval_results:
        avg_overall = sum(r.get("overall", 0) for r in eval_results) / len(eval_results)
        avg_patch = sum(r.get("patch_minimality", 0) for r in eval_results) / len(eval_results)
        avg_accuracy = sum(r.get("violation_accuracy", 0) for r in eval_results) / len(eval_results)
    else:
        avg_overall = avg_patch = avg_accuracy = 0.0

    result = {
        "evaluated_traces": len(eval_results),
        "avg_overall_score": round(avg_overall, 3),
        "avg_patch_minimality": round(avg_patch, 3),
        "avg_violation_accuracy": round(avg_accuracy, 3),
        "improvement_recommendations": list(set(improvement_hints)),
        "eval_timestamp": datetime.now(timezone.utc).isoformat(),
    }

    logger.info("[evals] Self-improvement loop complete: avg_score=%.3f", avg_overall)
    return result


def _fetch_recent_traces(api_key: str, n: int) -> List[dict]:
    """Fetch last N SENTINEL traces from Phoenix REST API."""
    try:
        import httpx
        base = os.environ.get("ARIZE_PHOENIX_BASE_URL", "https://app.phoenix.arize.com")
        headers = {"api_key": api_key, "Content-Type": "application/json"}

        resp = httpx.get(
            f"{base}/v1/spans",
            headers=headers,
            params={
                "project_name": "sentinel",
                "limit": n,
                "sort_by": "start_time",
                "sort_dir": "desc",
            },
            timeout=15,
        )
        if resp.status_code == 200:
            data = resp.json()
            spans = data.get("data", [])
            logger.info("[evals] Fetched %d spans from Phoenix", len(spans))
            return spans
        logger.warning("[evals] Phoenix spans fetch returned %d", resp.status_code)
        return []
    except Exception as exc:
        logger.error("[evals] Failed to fetch traces: %s", exc)
        return []


def _judge_trace(trace: dict) -> dict:
    """Run LLM-as-a-Judge evaluation on a single trace."""
    try:
        import google.generativeai as genai  # type: ignore
        model = genai.GenerativeModel("gemini-2.0-flash-exp")

        trace_summary = json.dumps({
            "span_id": trace.get("context", {}).get("span_id", "unknown"),
            "attributes": trace.get("attributes", {}),
            "events": trace.get("events", [])[:10],  # cap at 10 events
        }, indent=2)[:4000]  # cap tokens

        prompt = f"{JUDGE_SYSTEM_PROMPT}\n\nTrace to evaluate:\n{trace_summary}"
        response = model.generate_content(prompt)
        raw = response.text.strip()

        # Strip markdown code fences if present
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]

        scores = json.loads(raw)
        scores["span_id"] = trace.get("context", {}).get("span_id", "unknown")
        return scores
    except Exception as exc:
        logger.error("[evals] Judge failed for trace: %s", exc)
        return {
            "patch_minimality": 0.5,
            "violation_accuracy": 0.5,
            "quarantine_correctness": 0.5,
            "overall": 0.5,
            "reasoning": f"Eval failed: {exc}",
            "improvement_hint": "",
        }


def _write_evals_to_phoenix(api_key: str, eval_results: List[dict]) -> None:
    """Write evaluation scores back to Phoenix as annotations."""
    try:
        import httpx
        base = os.environ.get("ARIZE_PHOENIX_BASE_URL", "https://app.phoenix.arize.com")
        headers = {"api_key": api_key, "Content-Type": "application/json"}

        for result in eval_results:
            span_id = result.get("span_id")
            if not span_id or span_id == "unknown":
                continue
            payload = {
                "data": [{
                    "span_id": span_id,
                    "name": "sentinel_quality",
                    "annotator_kind": "LLM",
                    "result": {
                        "label": "good" if result.get("overall", 0) >= 0.75 else "needs_improvement",
                        "score": result.get("overall", 0.5),
                        "explanation": result.get("reasoning", ""),
                    },
                }]
            }
            httpx.post(
                f"{base}/v1/span_annotations",
                headers=headers,
                json=payload,
                timeout=10,
            )
        logger.info("[evals] Wrote %d eval scores back to Phoenix", len(eval_results))
    except Exception as exc:
        logger.error("[evals] Failed to write evals to Phoenix: %s", exc)
