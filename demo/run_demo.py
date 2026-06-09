import threading
import time
from demo.mocks import dynatrace_mock, elastic_mock, gitlab_mock, mongodb_mock, fivetran_mock, arize_mock
from agent.gateway.server import run as run_gateway
from agent.orchestrator import run_demo


def start_mocks():
    """Start mock MCP endpoints (Dynatrace, Elastic, GitLab, MongoDB, Fivetran, Arize)."""
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
    # wait for servers to boot
    time.sleep(2.0)


def start_gateway():
    """Start the Agent Gateway."""
    return threading.Thread(target=run_gateway, daemon=True)


def main():
    print("=" * 80)
    print("SENTINEL Stage 1→6 Demo: Autonomous Self-Healing End-to-End")
    print("=" * 80)
    print()
    
    print("[SETUP] Starting mock MCP endpoints on ports 9001/9002/9004/9005/9006/9007...")
    start_mocks()
    
    print("[SETUP] Starting Agent Gateway on port 9003...")
    gw_thread = start_gateway()
    gw_thread.start()
    time.sleep(1)
    
    print("[DEMO] Running Stage 1→6 orchestration flow (direct to mocks)...")
    print()
    run_demo(use_gateway=False)
    
    print()
    print("=" * 80)
    print("✓ Demo complete: Stage 1 → Stage 6 (Dynatrace→Elastic→GitLab→MongoDB→Fivetran→Arize)")
    print("=" * 80)


if __name__ == "__main__":
    main()

