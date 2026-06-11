"""Track metadata used by the publishing script.

Each track defines a slug, a partner name, a hero story (one-line + long),
and the partner-specific endpoints/keys it expects. The publishing script
turns this into a clean, distinct per-track repository layout.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List


@dataclass
class Track:
    slug: str
    partner: str
    title: str
    one_liner: str
    story: str
    hero_stage: str
    primary_color: str
    secrets: List[str] = field(default_factory=list)
    demo_command: str = "python -m demo.run_demo"
    extra_readme_sections: List[Dict[str, str]] = field(default_factory=list)


TRACKS: Dict[str, Track] = {
    "mongodb": Track(
        slug="mongodb",
        partner="MongoDB",
        title="SENTINEL · MongoDB Schema Continuity Agent",
        one_liner="Detect, validate, and contain MongoDB schema violations in under 60 seconds — without stopping live traffic.",
        story=(
            "When a deployment ships a bad schema change, your MongoDB collection doesn't crash. "
            "It silently ingests corrupt data. SENTINEL detects the violation, surgically relaxes the "
            "validator, quarantines the bad documents, and produces an incident report — while the "
            "application keeps writing."
        ),
        hero_stage="stage4_db_stabilize",
        primary_color="#47A248",
        secrets=["MONGODB_URI", "MONGODB_DATABASE"],
    ),
    "arize": Track(
        slug="arize",
        partner="Arize Phoenix",
        title="SENTINEL · Cognitive Integrity Agent for Arize Phoenix",
        one_liner="Score AI agent behavior, flag drift, and turn remediation traces into guardrail updates.",
        story=(
            "SENTINEL ingests its own self-healing traces into Arize Phoenix, evaluates them for "
            "prompt-injection risk, token efficiency, and decision quality, and returns a compliance "
            "score plus suggested guardrail updates."
        ),
        hero_stage="stage6_cognitive_assess",
        primary_color="#FF6B35",
        secrets=["ARIZE_PHOENIX_API_KEY", "ARIZE_PHOENIX_SPACE_ID"],
    ),
    "elastic": Track(
        slug="elastic",
        partner="Elastic",
        title="SENTINEL · Log Triage & Root-Cause Synthesis",
        one_liner="Turn raw log noise into structured incident intelligence using Elasticsearch.",
        story=(
            "SENTINEL queries Elastic within a precise time window around an alert, extracts canonical "
            "error strings and source file paths, and hands the structured signal to the next stage. "
            "No more scrolling through stack traces by hand."
        ),
        hero_stage="stage2_logs",
        primary_color="#005571",
        secrets=["ELASTIC_API_KEY", "ELASTIC_ENDPOINT"],
    ),
    "fivetran": Track(
        slug="fivetran",
        partner="Fivetran",
        title="SENTINEL · Downstream Pipeline Healer",
        one_liner="Keep warehouse pipelines healthy after upstream schema changes.",
        story=(
            "When a schema change ripples through your database, Fivetran connectors break. SENTINEL "
            "detects the drift, adjusts the connector mapping, and triggers a targeted resync — "
            "so analytics keep flowing."
        ),
        hero_stage="stage5_downstream_align",
        primary_color="#7D3C98",
        secrets=["FIVETRAN_API_KEY", "FIVETRAN_API_SECRET"],
    ),
    "gitlab": Track(
        slug="gitlab",
        partner="GitLab",
        title="SENTINEL · Code Remediation & MR Automation",
        one_liner="Open a hotfix branch and merge request with full audit context in under 10 seconds.",
        story=(
            "Given an error and a file path, SENTINEL uses GitLab to find the most likely culprit "
            "commit, creates a hotfix branch, and opens a merge request that includes the alert, "
            "stack trace, and remediation context — auditable end-to-end."
        ),
        hero_stage="stage3_git_remediation",
        primary_color="#FC6D26",
        secrets=["GITLAB_TOKEN", "GITLAB_API_URL"],
    ),
    "dynatrace": Track(
        slug="dynatrace",
        partner="Dynatrace",
        title="SENTINEL · Alert Ingestion & Service Isolation",
        one_liner="React to live service incidents in milliseconds, not minutes.",
        story=(
            "SENTINEL ingests Dynatrace alerts, isolates the affected service and pod, and produces "
            "an isolation token that scopes every downstream action. The rest of the healing pipeline "
            "operates on a tightly bounded blast radius."
        ),
        hero_stage="stage1_ingest",
        primary_color="#1496FF",
        secrets=["DYNATRACE_TOKEN", "DYNATRACE_ENV"],
    ),
}


def get(slug: str) -> Track:
    if slug not in TRACKS:
        raise KeyError(f"unknown track: {slug}. known: {list(TRACKS)}")
    return TRACKS[slug]
