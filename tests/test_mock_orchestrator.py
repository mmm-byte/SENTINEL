"""Tests for the mock orchestrator used by the SRE Control Cockpit."""
from __future__ import annotations

import time

from agent.mock_orchestrator import MockOrchestrator


def test_initial_status_is_idle():
    m = MockOrchestrator()
    s = m.status()
    assert s["mode"] == "MOCK"
    assert s["run_id"] is None
    for sid in (
        "stage1_ingest", "stage2_logs", "stage3_git_remediation",
        "stage4_db_stabilize", "stage5_downstream_align",
        "stage6_cognitive_assess",
    ):
        assert s["stages"][sid]["status"] == "idle"


def test_trigger_starts_run_and_pauses_at_stage4():
    m = MockOrchestrator()
    run_id = m.trigger()
    assert run_id
    # Drive the background thread for a short time and expect it to
    # advance past stage 3 and stop at stage 4 awaiting approval.
    for _ in range(40):
        s = m.status()
        if s["approval_pending"]:
            break
        time.sleep(0.1)
    s = m.status()
    assert s["approval_pending"] is not None
    assert s["approval_pending"]["stage_id"] == "stage4_db_stabilize"
    # The earlier stages should have completed by now.
    assert s["stages"]["stage1_ingest"]["status"] == "success"
    assert s["stages"]["stage2_logs"]["status"] == "success"
    assert s["stages"]["stage3_git_remediation"]["status"] == "success"


def test_approve_lets_run_complete():
    m = MockOrchestrator()
    m.trigger()
    # Wait for the run to reach the approval gate.
    for _ in range(200):
        if m.status()["approval_pending"]:
            break
        time.sleep(0.1)
    assert m.status()["approval_pending"] is not None
    m.approve()
    # Wait for the run to complete (the post-approval stages take ~2.5s).
    for _ in range(200):
        s = m.status()
        if s["mttr"] is not None:
            break
        time.sleep(0.1)
    s = m.status()
    assert s["mttr"] is not None and s["mttr"] > 0
    assert s["compliance"] is not None
    assert s["approval_pending"] is None


def test_reject_marks_run_failed():
    m = MockOrchestrator()
    m.trigger()
    for _ in range(40):
        if m.status()["approval_pending"]:
            break
        time.sleep(0.1)
    m.reject()
    s = m.status()
    assert s["approval_pending"] is None
    # The mock flips any running stage to failed on reject.
    for sid, st in s["stages"].items():
        if st["status"] == "running":
            assert st["status"] == "failed"  # never reached
