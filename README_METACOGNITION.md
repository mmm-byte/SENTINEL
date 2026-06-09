# PROJECT METACOGNITION

## The Cross-Domain Autonomous Self-Healing Conductor

**An AI-powered agent that orchestrates automated incident remediation across six enterprise platforms using the Model Context Protocol (MCP) over JSON-RPC 2.0.**

---

## 📋 Overview

Project Metacognition transforms large language models from conversational assistants into a **unified, proactive Site Reliability Engineer (SRE)**. When a critical production incident occurs, the system executes an automated cognitive relay across six distinct operational domains:

1. **Dynatrace** (Ingestion & Node Isolation)
2. **Elastic** (Log Signature Processing)
3. **GitLab** (Root Cause Auditing & Branch Creation)
4. **MongoDB** (Database State Stabilization)
5. **Fivetran** (Downstream Pipeline Alignment)
6. **Arize** (Cognitive Integrity Assessment)

Instead of relying on fragmented webhooks, the system standardizes communication using **MCP via remote HTTP endpoints over JSON-RPC 2.0**, allowing the central Gemini model to securely invoke tools and mutate states across entirely separate enterprise platforms.

---

## 🏗️ Architecture

### Core Components

- **Central Orchestrator** (`agent/orchestrator.py`)  
  Coordinates the multi-stage self-healing flow by issuing JSON-RPC requests to partner MCP servers.

- **Agent Gateway** (`agent/gateway/server.py`)  
  Centralized, auditable outbound proxy enforcing IAM, request validation, and response scrubbing via Model Armor.

- **MCP Adapters** (`agent/mcp_adapters/`)  
  Partner-specific implementations for Dynatrace, Elastic, GitLab, MongoDB, Fivetran, and Arize.

- **JSON-RPC Client** (`agent/jsonrpc/client.py`)  
  Lightweight HTTP client for MCP JSON-RPC 2.0 communication with retry logic and audit logging.

- **SRE Control Cockpit** (`ui/index.html` + `agent/ui_server.py`)  
  Judge-facing dashboard showing real-time system topology, incident progression, and remediation status.

---

## 🚀 Quick Start

### Prerequisites

- Python 3.10+
- Dependencies in `requirements.txt` (httpx, fastapi, uvicorn, pydantic, etc.)

### Installation

```bash
# Clone or navigate to the SENTINEL repo
cd /Users/mahindragupthakotha/Git\ Repo/SENTINEL

# Install dependencies
python -m pip install -r requirements.txt

# Configure Python environment
python -c "from agent.orchestrator import Orchestrator; print('✓ Environment ready')"
```

### Run the Full Demo

The demo spins up local mock MCP endpoints, the gateway, and orchestrator:

```bash
PYTHONPATH=. python demo/run_demo.py
```

Or for the complete experience with the UI:

```bash
PYTHONPATH=. python demo/run_full_demo.py
```

Then open: **http://localhost:8080**

---

## 📊 The 6-Stage Self-Healing Loop

### Stage 1: Ingestion & Node Isolation (Dynatrace)

- **Trigger:** Dynatrace alert on application degradation (e.g., HTTP 500 spike).
- **Action:** Query Dynatrace topology to isolate affected pod, service, and container.
- **Output:** `{service_id, pod_id, container_signature, time_window}`

### Stage 2: Log Signature Processing (Elastic)

- **Input:** Service ID, pod ID, and time window from Stage 1.
- **Action:** Execute time-bounded Elasticsearch query to extract error stack traces.
- **Output:** `{error_string, file_path, sample_log_entries}`

### Stage 3: Root Cause Auditing & Branch Creation (GitLab)

- **Input:** Error string and file path from Stage 2.
- **Actions:**
  - Run `git blame` to find recent commits affecting the file.
  - Create a hotfix branch: `hotfix/auto/<timestamp>-<agent_id>`.
  - Open a Merge Request with automated code diff reasoning.
- **Output:** `{branch, merge_request_url, suspected_commit_sha}`

### Stage 4: Database State Stabilization (MongoDB)

- **Input:** Schema patch metadata from Stage 3.
- **Action:** Run safe `collMod` to downgrade validation action from "error" to "warn".
- **Output:** Collection modification metadata and validation rules.

### Stage 5: Downstream Pipeline Alignment (Fivetran)

- **Input:** Collection modification metadata from Stage 4.
- **Action:** Adjust connector schema mappings and trigger resync.
- **Output:** Resync status and connector logs.

### Stage 6: Cognitive Integrity Assessment (Arize)

- **Input:** Full execution trace, prompts, token usage.
- **Action:** Ingest spans via Phoenix/Arize and score for injection risk, token efficiency.
- **Output:** Compliance report and drift assessment.

---

## 📁 Project Structure

```
SENTINEL/
├── agent/
│   ├── __init__.py
│   ├── config.py
│   ├── main.py
│   ├── orchestrator.py          # Central coordinator
│   ├── ui_server.py             # Cockpit FastAPI server
│   ├── jsonrpc/
│   │   ├── __init__.py
│   │   └── client.py            # JSON-RPC HTTP client
│   ├── mcp_adapters/
│   │   ├── __init__.py
│   │   └── gitlab.py            # GitLab MCP adapter
│   ├── gateway/
│   │   ├── __init__.py
│   │   └── server.py            # Agent Gateway
│   └── tools/
│       ├── __init__.py
│       ├── incident_reporter.py
│       ├── payload_validator.py
│       ├── quarantine_manager.py
│       ├── schema_inspector.py
│       └── schema_patcher.py
├── demo/
│   ├── __init__.py
│   ├── run_demo.py              # Stage 1→3 demo runner
│   ├── run_full_demo.py         # Full demo with UI
│   ├── setup_demo_collection.py
│   ├── inject_schema_drift.py
│   └── mocks/
│       ├── __init__.py
│       ├── dynatrace_mock.py    # Mock MCP endpoint (Dynatrace)
│       ├── elastic_mock.py      # Mock MCP endpoint (Elastic)
│       └── gitlab_mock.py       # Mock MCP endpoint (GitLab)
├── ui/
│   └── index.html               # SRE Control Cockpit UI
├── docs/
│   └── implementation_plan.md   # Detailed architecture & design
├── tests/
│   └── test_tools.py
├── requirements.txt
├── README.md                    # This file
└── LICENSE
```

---

## 🔄 Running the Demo

### Option 1: Stage 1→3 Flow (Recommended for Quick Test)

```bash
PYTHONPATH=. python demo/run_demo.py
```

**Output:**
```
================================================================================
SENTINEL Stage 1→3 Demo: Autonomous Self-Healing End-to-End
================================================================================

[SETUP] Starting mock MCP endpoints on ports 9001/9002/9004...
[SETUP] Starting Agent Gateway on port 9003...
[DEMO] Running Stage 1→3 orchestration flow (direct to mocks)...

[orchestrator] Stage 1: asking Dynatrace for topology
[orchestrator] Dynatrace result: {'service_id': 'svc-payments', 'pod_id': 'k8s-pod-x92-node4', ...}

[orchestrator] Stage 2: querying Elastic logs
[orchestrator] Elastic result: {'error_string': 'BSONType mismatch...', 'file_path': 'src/payments/processor.py', ...}

[orchestrator] Stage 3: GitLab remediation (blame, branch, MR)
[orchestrator] GitLab result: {'branch': 'hotfix/auto/2026-06-09-...', 'merge_request_url': 'https://gitlab.com/org/repo/-/merge_requests/42', ...}

================================================================================
✓ Demo complete: Stage 1 (Dynatrace) → Stage 2 (Elastic) → Stage 3 (GitLab)
================================================================================
```

### Option 2: Full Demo with UI (Press Ctrl+C to Exit)

```bash
PYTHONPATH=. python demo/run_full_demo.py
```

Then open your browser:

```
http://localhost:8080
```

The UI displays:
- **Real-time system topology** with animated stage nodes
- **Live execution timeline** showing each MCP call and result
- **Health metrics** (MTTD, MTTR, system status)
- **Interactive right panel** with error details and MR links

---

## 🔌 JSON-RPC 2.0 Message Format

All MCP calls use JSON-RPC 2.0 over HTTP POST.

### Request Example

```json
{
  "jsonrpc": "2.0",
  "id": "b2e3d6a4-...",
  "method": "mcp.exec",
  "params": {
    "action": "query_topology",
    "payload": {
      "alert_id": "demo-alert-1"
    },
    "agent_id": "agent-0a1b2c"
  }
}
```

### Response Example (Success)

```json
{
  "jsonrpc": "2.0",
  "id": "b2e3d6a4-...",
  "result": {
    "service_id": "svc-payments",
    "pod_id": "k8s-pod-x92-node4",
    "container_signature": "sha256:deadbeef",
    "time_window": "2026-06-09T10:00:00Z/2026-06-09T10:02:00Z"
  }
}
```

### Response Example (Error)

```json
{
  "jsonrpc": "2.0",
  "id": "b2e3d6a4-...",
  "error": {
    "code": -32601,
    "message": "Method not found"
  }
}
```

---

## 🛡️ Security & Governance

- **Agent Identity:** Every sub-agent gets a unique cryptographic ID mapped to a GCP Service Account.
- **Audit Trail:** All requests signed with HMAC/JWT; persist audit events to Cloud Logging.
- **Model Armor:** Inline safety proxy scrubbing inputs/outputs for prompt injection risk.
- **Workload Identity:** Use GCP IAM to map agent_id → service account for secure downstream calls.

---

## 🎨 UI/UX Design — SRE Control Cockpit

The cockpit is designed for judges to see true multi-agent coordination in real-time:

- **Dark-slate theme** (#0E1117) with partner-branded stage nodes
- **Status indicators:** Crimson (critical), Amber (active), Emerald (success)
- **Animated pipeline traces** highlighting the error remediation path
- **Expandable timeline** showing each RPC call and duration
- **Approve/Reject toggles** for human-in-loop safety interventions

---

## 📚 Implementation Details

### Central Orchestrator API

```python
from agent.orchestrator import Orchestrator

orch = Orchestrator(
    dynatrace_endpoint="http://...",
    elastic_endpoint="http://...",
    gitlab_endpoint="http://..."
)

# Stage 1
dt = orch.stage1_ingest(alert_id="alert-123")

# Stage 2
es = orch.stage2_logs(
    service_name=dt["service_id"],
    pod_id=dt["pod_id"],
    window=dt["time_window"]
)

# Stage 3
git = orch.stage3_git_remediation(
    error_string=es["error_string"],
    file_path=es["file_path"],
    pod_id=dt["pod_id"]
)
```

### Agent Gateway

The gateway serves as a centralized audit point. All orchestrator calls can be routed through it:

```python
# Instead of direct MCP calls, orchestrator posts to gateway:
POST /proxy HTTP/1.1
Host: localhost:9003
X-Agent-ID: agent-0a1b2c
Authorization: Bearer <token>

{
  "jsonrpc": "2.0",
  "id": "...",
  "method": "mcp.exec",
  "params": {
    "endpoint": "http://dynatrace-mcp:9001/mcp",
    "payload": { ... }
  }
}
```

---

## 🚢 Deployment & Operations

### Google Cloud Run

Deploy to Cloud Run for auto-scaling:

```bash
gcloud run deploy sentinel-orchestrator \
  --source . \
  --platform managed \
  --region us-central1 \
  --no-allow-unauthenticated
```

### Observability

- **Logs:** Cloud Logging integration (structured JSON audit events)
- **Traces:** OpenTelemetry export to Cloud Trace
- **Metrics:** Prometheus-compatible metrics endpoint

---

## 🎯 Next Steps

1. **Stage 4–6 Implementation:** Add MongoDB, Fivetran, and Arize adapters.
2. **Safety Policies:** Integrate OPA for advanced access control and guardrails.
3. **Production Hardening:** mTLS for gateway, signed JWTs, rate limiting.
4. **Observability:** Connect to real Cloud Logging, Trace, and Monitoring.
5. **Documentation:** Full operator runbooks and troubleshooting guides.

---

## 📖 Documentation

- [Implementation Plan](docs/implementation_plan.md) — Detailed architecture, phase breakdown, and design decisions.
- [Hackathon Brief](Hackathon%20Details.txt) — Challenge requirements and judging criteria.

---

## 📄 License

This project is provided under an open-source license (see `LICENSE` file).

---

## 🙋 Support & Questions

For questions about the architecture or to discuss implementation details, refer to the [implementation plan](docs/implementation_plan.md) or reach out via the repository issues.

---

**Built for the Google Cloud Rapid Agent Hackathon 2026**  
*Powered by Gemini, MCP, and Google Cloud Agent Builder*
