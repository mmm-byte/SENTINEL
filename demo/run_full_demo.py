#!/usr/bin/env python3
"""
SENTINEL Complete Launcher
===========================
Starts all components: mocks, gateway, orchestrator, and UI cockpit.

Usage:
    python -m demo.run_full_demo
    Then open: http://localhost:8080
"""

import threading
import time
import sys
from demo.mocks import dynatrace_mock, elastic_mock, gitlab_mock, mongodb_mock, fivetran_mock, arize_mock
from agent.gateway.server import run as run_gateway
from agent.ui_server import run as run_ui
from agent.orchestrator import run_demo


def start_mocks():
    """Start mock MCP endpoints (Dynatrace, Elastic, GitLab, MongoDB, Fivetran, Arize)."""
    print("[MOCKS] Starting Dynatrace (9001), Elastic (9002), GitLab (9004), MongoDB (9005), Fivetran (9006), Arize (9007)...")
    t1 = threading.Thread(target=dynatrace_mock.run, daemon=True)
    t2 = threading.Thread(target=elastic_mock.run, daemon=True)
    t3 = threading.Thread(target=gitlab_mock.run, daemon=True)
    t4 = threading.Thread(target=mongodb_mock.run, daemon=True)
    t5 = threading.Thread(target=fivetran_mock.run, daemon=True)
    t6 = threading.Thread(target=arize_mock.run, daemon=True)
    t1.start()
    t2.start()
    t3.start()
    t4.start()
    t5.start()
    t6.start()
    time.sleep(2.0)
    print("[MOCKS] ✓ Ready")


def start_gateway():
    """Start the Agent Gateway."""
    print("[GATEWAY] Starting on port 9003...")
    t = threading.Thread(target=run_gateway, daemon=True)
    t.start()
    time.sleep(1)
    print("[GATEWAY] ✓ Ready")


def start_ui():
    """Start the SRE Control Cockpit UI."""
    print("[UI] Starting SRE Control Cockpit on port 8080...")
    t = threading.Thread(target=run_ui, daemon=True)
    t.start()
    time.sleep(1)
    print("[UI] ✓ Ready at http://localhost:8080")


def main():
    print("=" * 80)
    print("SENTINEL — Complete End-to-End Demo with UI Cockpit")
    print("=" * 80)
    print()

    try:
        start_mocks()
        start_gateway()
        start_ui()

        print()
        print("=" * 80)
        print("🎯 LAUNCHING ORCHESTRATION PIPELINE")
        print("=" * 80)
        print()

        # Run the full Stage 1→6 demo
        run_demo(use_gateway=False)

        print()
        print("=" * 80)
        print("✓ Orchestration Complete!")
        print("=" * 80)
        print()
        print("📊 View live cockpit at: http://localhost:8080")
        print()
        print("Press Ctrl+C to exit...")
        print()

        # Keep the script running
        while True:
            time.sleep(1)

    except KeyboardInterrupt:
        print()
        print("Shutting down...")
        sys.exit(0)


if __name__ == "__main__":
    main()
