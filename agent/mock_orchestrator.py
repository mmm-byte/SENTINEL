"""Mock orchestrator used by the UI when live demo mocks are not running.

This keeps the SRE Control Cockpit usable for judges and reviewers with
zero setup: open the page, click "Trigger Healing Run", and watch all
six stages progress from idle → running → success/failed.
"""
from __future__ import annotations

import threading
import time
import uuid
from dataclasses import dataclass, field
from typing import Dict, List, Optional


STAGE_ORDER = [
    ("stage1_ingest",           "Dynatrace",  "check"),
    ("stage2_logs",             "Elastic",    "check"),
    ("stage3_git_remediation",  "GitLab",     "fix"),
    ("stage4_db_stabilize",     "MongoDB",    "ask"),
    ("stage5_downstream_align", "Fivetran",   "fix"),
    ("stage6_cognitive_assess", "Arize",      "check"),
]


@dataclass
class _Stage:
    status: str = "idle"
    started_at: Optional[float] = None
    finished_at: Optional[float] = None
    message: str = ""


@dataclass
class _Run:
    run_id: str
    started_at: float
    finished_at: Optional[float] = None
    stages: Dict[str, _Stage] = field(default_factory=dict)
    approval_pending: Optional[Dict[str, str]] = None
    last_event: Optional[Dict[str, str]] = None
    mttd: Optional[float] = None
    mttr: Optional[float] = None
    compliance: Optional[float] = None


class MockOrchestrator:
    """Thread-safe mock that drives a 6-stage healing loop in the background."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._current: Optional[_Run] = None
        self._last_update: float = 0.0
        self._mode = "MOCK"

    # ── public API ─────────────────────────────────────────────────────────
    def status(self) -> dict:
        with self._lock:
            if self._current is None:
                stages = {sid: _Stage().__dict__ for sid, _, _ in STAGE_ORDER}
            else:
                stages = {sid: s.__dict__.copy() for sid, s in self._current.stages.items()}
                # also include stages not yet touched
                for sid, _, _ in STAGE_ORDER:
                    stages.setdefault(sid, _Stage().__dict__)

            return {
                "mode": self._mode,
                "run_id": self._current.run_id if self._current else None,
                "last_update": self._last_update or None,
                "stages": stages,
                "approval_pending": self._current.approval_pending if self._current else None,
                "last_event": self._current.last_event if self._current else None,
                "mttd": self._current.mttd if self._current else None,
                "mttr": self._current.mttr if self._current else None,
                "compliance": self._current.compliance if self._current else None,
            }

    def trigger(self) -> str:
        with self._lock:
            if self._current and self._current.finished_at is None:
                return self._current.run_id
            run = _Run(run_id=str(uuid.uuid4())[:8], started_at=time.time())
            for sid, _, _ in STAGE_ORDER:
                run.stages[sid] = _Stage()
            self._current = run
            self._last_update = time.time()
            run.last_event = {"message": f"Run {run.run_id} queued", "level": "info"}
        t = threading.Thread(target=self._drive, args=(run.run_id,), daemon=True)
        t.start()
        return run.run_id

    def approve(self) -> None:
        with self._lock:
            if not self._current or not self._current.approval_pending:
                return
            self._current.approval_pending = None
            self._current.last_event = {"message": "Operator approved Stage 4", "level": "ok"}
            self._last_update = time.time()
        # Restart the background thread to continue past Stage 4
        run_id = self._current.run_id
        t = threading.Thread(target=self._continue_from_stage4, args=(run_id,), daemon=True)
        t.start()

    def _continue_from_stage4(self, run_id: str) -> None:
        """Resume the run after Stage 4 approval."""
        for idx, (sid, partner, phase) in enumerate(STAGE_ORDER[4:], start=5):
            with self._lock:
                if not self._current or self._current.run_id != run_id:
                    return
                st = self._current.stages[sid]
                st.status = "running"
                st.started_at = time.time()
                st.message = f"calling {partner}…"
                self._current.last_event = {
                    "message": f"Stage {idx}: {partner} — {phase}",
                    "level": "info",
                }
                self._last_update = time.time()

            time.sleep(0.6)

            with self._lock:
                if not self._current or self._current.run_id != run_id:
                    return
                st = self._current.stages[sid]
                st.finished_at = time.time()
                st.status = "success"
                st.message = f"{partner} OK"
                self._current.last_event = {
                    "message": f"Stage {idx}: {partner} success",
                    "level": "ok",
                }
                self._last_update = time.time()

        # 3) finalize
        with self._lock:
            if not self._current or self._current.run_id != run_id:
                return
            self._current.finished_at = time.time()
            self._current.mttr = self._current.finished_at - self._current.started_at
            self._current.compliance = 0.97
            self._current.last_event = {
                "message": f"Run complete in {self._current.mttr:.1f}s",
                "level": "ok",
            }
            self._last_update = time.time()

    def reject(self) -> None:
        with self._lock:
            if not self._current:
                return
            self._current.approval_pending = None
            for sid, _, _ in STAGE_ORDER:
                st = self._current.stages[sid]
                if st.status == "running":
                    st.status = "failed"
                    st.message = "rejected by operator"
                    st.finished_at = time.time()
            self._current.finished_at = time.time()
            self._current.last_event = {"message": "Run rejected by operator", "level": "bad"}
            self._last_update = time.time()

    # ── internal driver ────────────────────────────────────────────────────
    def _drive(self, run_id: str) -> None:
        # 1) alert
        time.sleep(0.4)
        with self._lock:
            if not self._current or self._current.run_id != run_id:
                return
            self._current.mttd = 0.42
            self._current.last_event = {"message": "Alert ingested (mock)", "level": "info"}
            self._last_update = time.time()

        # 2) drive each stage
        for idx, (sid, partner, phase) in enumerate(STAGE_ORDER, start=1):
            with self._lock:
                if not self._current or self._current.run_id != run_id:
                    return
                if self._current.approval_pending:
                    return  # paused for approval
                st = self._current.stages[sid]
                st.status = "running"
                st.started_at = time.time()
                st.message = f"calling {partner}…"
                self._current.last_event = {
                    "message": f"Stage {idx}: {partner} — {phase}",
                    "level": "info",
                }
                self._last_update = time.time()

            time.sleep(0.6 if phase != "ask" else 0.4)

            with self._lock:
                if not self._current or self._current.run_id != run_id:
                    return
                st = self._current.stages[sid]
                st.finished_at = time.time()

                # Stage 4 pauses for human approval
                if sid == "stage4_db_stabilize":
                    st.status = "awaiting_approval"
                    st.message = "schema change requires human approval"
                    self._current.approval_pending = {
                        "stage_id": sid,
                        "reason": "MongoDB collMod requested",
                    }
                    self._current.last_event = {
                        "message": "Stage 4 awaiting operator approval",
                        "level": "warn",
                    }
                    self._last_update = time.time()
                    return

                st.status = "success"
                st.message = f"{partner} OK"
                self._current.last_event = {
                    "message": f"Stage {idx}: {partner} success",
                    "level": "ok",
                }
                self._last_update = time.time()

        # 3) finalize
        with self._lock:
            if not self._current or self._current.run_id != run_id:
                return
            self._current.finished_at = time.time()
            self._current.mttr = self._current.finished_at - self._current.started_at
            self._current.compliance = 0.97
            self._current.last_event = {
                "message": f"Run complete in {self._current.mttr:.1f}s",
                "level": "ok",
            }
            self._last_update = time.time()
