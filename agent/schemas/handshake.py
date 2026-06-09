"""
Handshake — the first-class shared schema that flows between every stage of
the SENTINEL 6-stage self-healing loop.

Truthful design notes
---------------------
- A new `Handshake` is created at Stage 1 (Dynatrace) and is the single object
  that every subsequent stage receives, mutates, and forwards.
- Optional fields exist for data that only appears in later stages
  (e.g. `commit_sha` is unknown until Stage 3).
- `correlation_id` and `agent_id` are required for distributed tracing; the
  orchestrator auto-fills them if missing.
- A `to_json_rpc_params()` helper is provided so stages can hand the data
  straight to the JSON-RPC client without rebuilding dicts.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator


class Stage(str, Enum):
    INGEST = "stage1_ingest"
    LOGS = "stage2_logs"
    GIT = "stage3_git_remediation"
    DB = "stage4_db_stabilize"
    PIPELINE = "stage5_downstream_align"
    COGNITIVE = "stage6_cognitive_assess"


class Handshake(BaseModel):
    """
    The single context object passed between every stage of the healing loop.

    Field usage by stage:
      Stage 1 (Dynatrace)  → produces: service_id, pod_id, time_window, isolation_token
      Stage 2 (Elastic)    → adds:     error_string, file_path, line_number, sample_log_entries
      Stage 3 (GitLab)     → adds:     branch, merge_request_url, suspected_commit_sha, patch_summary
      Stage 4 (MongoDB)    → adds:     schema_patch, quarantine_collection
      Stage 5 (Fivetran)   → adds:     resync_status
      Stage 6 (Arize)      → adds:     compliance_score, drift_score
    """

    # --- identity & tracing (required) ---------------------------------------
    correlation_id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        description="Distributed-trace ID. One per healing run. Auto-generated.",
    )
    agent_id: str = Field(
        default="agent-unknown",
        description="Identity of the sub-agent that produced/owns this handshake.",
    )
    origin_stage: Optional[Stage] = Field(
        default=None,
        description="The stage that most-recently produced/updated this handshake.",
    )
    timestamp: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description="ISO-8601 UTC timestamp of the most recent update.",
    )

    # --- Stage 1 (Dynatrace) -------------------------------------------------
    service_id: Optional[str] = None
    pod_id: Optional[str] = None
    container_signature: Optional[str] = None
    time_window: Optional[str] = None
    isolation_token: Optional[str] = None
    alert_id: Optional[str] = None

    # --- Stage 2 (Elastic) ---------------------------------------------------
    error_string: Optional[str] = None
    file_path: Optional[str] = None
    line_number: Optional[int] = None
    sample_log_entries: List[str] = Field(default_factory=list)

    # --- Stage 3 (GitLab) ----------------------------------------------------
    branch: Optional[str] = None
    merge_request_url: Optional[str] = None
    suspected_commit_sha: Optional[str] = None
    patch_summary: Optional[str] = None

    # --- Stage 4 (MongoDB) ---------------------------------------------------
    schema_patch: Optional[Dict[str, Any]] = None
    quarantine_collection: Optional[str] = None

    # --- Stage 5 (Fivetran) --------------------------------------------------
    resync_status: Optional[str] = None

    # --- Stage 6 (Arize) -----------------------------------------------------
    compliance_score: Optional[float] = None
    drift_score: Optional[float] = None

    # --- audit trail ---------------------------------------------------------
    audit_trail: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Append-only log of stage transitions for traceability.",
    )

    # --- validators ----------------------------------------------------------
    @field_validator("compliance_score", "drift_score")
    @classmethod
    def _score_in_range(cls, v: Optional[float]) -> Optional[float]:
        if v is None:
            return v
        if not 0.0 <= v <= 1.0:
            raise ValueError(f"score must be in [0.0, 1.0], got {v}")
        return v

    # --- helpers -------------------------------------------------------------
    def record_stage(self, stage: Stage, summary: str, **extra: Any) -> "Handshake":
        """Append an audit entry and return self (chainable)."""
        entry: Dict[str, Any] = {
            "stage": stage.value,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "summary": summary,
        }
        entry.update(extra)
        self.audit_trail.append(entry)
        self.origin_stage = stage
        self.timestamp = entry["timestamp"]
        return self

    def to_json_rpc_params(self, action: str) -> Dict[str, Any]:
        """Render the handshake as a JSON-RPC `params` envelope for an MCP call."""
        return {
            "action": action,
            "payload": self.model_dump(exclude_none=True),
            "correlation_id": self.correlation_id,
            "agent_id": self.agent_id,
        }

    @classmethod
    def from_stage1(
        cls,
        alert_id: str,
        service_id: str,
        pod_id: str,
        time_window: str,
        container_signature: Optional[str] = None,
        agent_id: str = "agent-dynatrace",
    ) -> "Handshake":
        """Factory for the first stage's output."""
        h = cls(
            alert_id=alert_id,
            service_id=service_id,
            pod_id=pod_id,
            container_signature=container_signature,
            time_window=time_window,
            isolation_token=str(uuid.uuid4()),
            agent_id=agent_id,
            origin_stage=Stage.INGEST,
        )
        h.record_stage(Stage.INGEST, f"isolated pod {pod_id} for alert {alert_id}")
        return h
