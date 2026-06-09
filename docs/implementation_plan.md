Project Metacognition — Implementation Plan
=========================================

Overview
--------
This document describes a concrete, implementable plan for Project Metacognition: a Cross-Domain Autonomous Self-Healing Conductor. It covers the core orchestration components, per-stage implementations (the 6-stage self-healing loop), partner MCP adapters, runtime, testing strategy, deployment notes, and a dedicated UI/UX design placeholder for the SRE Control Cockpit.

Goals
-----
- Implement a secure Central Orchestrator that speaks MCP via JSON-RPC 2.0
- Build lightweight Agent Gateway for outbound authenticated calls
- Provide per-partner MCP adapters (Dynatrace, Elastic, GitLab, MongoDB, Fivetran, Arize)
- Prototype Stage 1–3 flow end-to-end with local mocks
- Provide production-ready deployment notes (Cloud Run) and observability
- Deliver a judge-facing UI/UX cockpit mockup area

Repository layout (suggested)
----------------------------
- `agent/` — core orchestrator, adapters, tools
- `agent/gateway/` — Agent Gateway HTTP server
- `agent/mcp_adapters/` — `dynatrace.py`, `elastic.py`, `gitlab.py`, `mongodb.py`, `fivetran.py`, `arize.py`
- `demo/` — local mock endpoints and demo orchestration
- `docs/implementation_plan.md` — this file
- `tests/` — unit & integration tests

Core Components — Design & Implementation Details
-----------------------------------------------
1) Central Orchestrator (MCP client + JSON-RPC dispatcher)

- Purpose: Orchestrates multi-stage flows, issues JSON-RPC requests to partner MCP servers (over HTTP), sequences responses, performs retries and audit logging.
- Tech: Python 3.10+, `httpx` for HTTP, `pydantic` for message schemas, `fastapi` for an internal control API.
- JSON-RPC 2.0 wrapper: implement a small client with following features:
  - `call_method(method: str, params: dict, endpoint: str, timeout=30s) -> result`
  - request id generation (UUIDv4), timeout handling, exponential backoff for transient errors
  - idempotency token support when mutating partner state
  - audit log entries: {request_id, method, params_hash, caller_agent_id, timestamp, status}
- Example JSON-RPC request

  {
    "jsonrpc": "2.0",
    "method": "mcp.execute",
    "params": {"action": "query_topology", "query": {"service": "payments"}},
    "id": "b2e3d6a4-..."
  }

- Response handling: validate `jsonrpc` + `result` or handle `error` per JSON-RPC spec.

2) Agent Gateway (HTTP server, auth, routing)

- Purpose: Centralized, auditable outbound proxy for all partner API calls. Enforces IAM, service account impersonation, TLS, request/response scrubbing via Model Armor.
- Tech: `fastapi` + `uvicorn` or lightweight Go server if desired for perf.
- Responsibilities:
  - Validate incoming orchestrator requests (mutual TLS or signed JWT)
  - Map agent identity to GCP service account credentials (impersonation flow)
  - Route requests to partner `endpoint` with added headers and signing
  - Central logging to Cloud Logging; emit structured audit events

3) Model Armor (safety proxy)

- Purpose: Inline policy enforcement and prompt-injection mitigation for all text or model-derived data crossing trust boundaries.
- Implementation:
  - A validation pipeline that accepts a `payload` and runs: token-limit checks, denylist/allowlist regex, JSON-schema validation, and a small prompt-injection heuristic (e.g., detect 'execute', 'delete', 'drop' patterns in free text contexts).
  - Hooks: Pre-send (sanitize params) and post-receive (inspect results) policies.

4) Agent Identity & Audit

- Every sub-agent is assigned a deterministic cryptographic `agent_id` (UUID + public key fingerprint) mapped to a specific GCP Service Account.
- Use Google IAM Workload Identity or service-account impersonation for downstream calls.
- Sign each JSON-RPC request with an HMAC or JWT claiming `agent_id` to ensure traceability.

5) MCP Adapter Pattern

- Each partner adapter implements a small interface:
  - `discover(endpoint)` — health and capability discovery
  - `query(params)` — read-like calls
  - `mutate(params)` — write-like calls with idempotency
  - `translate_to_local_schema(result)` — normalize outputs
- Example adapter responsibilities:
  - Dynatrace: query topology, incidents, metrics windows
  - Elastic: run time-bounded searches, ingest/parse stack traces
  - GitLab: run blame, create branches, open merge requests via repo APIs
  - MongoDB: run `collMod`, adjust validators, perform safe rollbacks
  - Fivetran: adjust connector mapping, trigger resyncs
  - Arize: ingest spans/traces and run evaluation scoring

Stage-by-Stage Implementation (6-Stage Self-Healing Loop)
-------------------------------------------------------
General pattern for each stage
- Input: validated `handshake` object from previous stage
- Core flow: call partner adapter → normalize results → decide next action → log and emit audit trace
- Failure modes: backoff+retry for transient errors; fallback to human alert/escallation after N tries

Stage 1 — Ingestion & Node Isolation (Dynatrace)
- Trigger: incoming Dynatrace alert webhook or polling.
- Actions:
  - Use `dynatrace.mcp.query_topology({alert_id, timeframe})` to map alert to `service_id`, `pod_id`, `container_signature`.
  - Produce `isolation_token` and forward to Stage 2 with: {service_name, pod_id, precise_timestamp_window}
- Output: structured object for log search filtering.

Stage 2 — Log Signature Processing (Elastic)
- Input: `{service_name, pod_id, window}`
- Actions:
  - Build a time-bounded Elasticsearch DSL query based on the window and container signature
  - Extract error stack traces and canonicalize exception strings
  - Attempt source file path extraction via regex/stack parsing
- Output: `{error_string, file_path, line_number?, sample_log_entries}`

Stage 3 — Root Cause Auditing & Branch Creation (GitLab)
- Input: `{error_string, file_path, pod_id}`
- Actions:
  - Run `git blame` equivalent via code search and GitLab APIs to find recent commit(s)
  - Create hotfix branch: `hotfix/auto/<timestamp>-<agent_id>`
  - Run automated static checks (unit tests via GitLab pipelines) and attach results to MR
  - Create MR description including human-friendly reasoning and commit references
- Output: `{branch, merge_request_url, suspected_commit_sha, patch_summary}`

Stage 4 — Database State Stabilization (MongoDB)
- Input: `{suspected_commit_sha, patch_summary, file_path}`
- Actions:
  - If runtime errors are due to schema rejection, run a safe `collMod` via MongoDB MCP adapter to change validator action to `warn` or add coercion rules.
  - Quarantine broken payloads into a side collection for later reconciliation
  - Emit a schema modification event with idempotency token
- Safety: require approval policy for certain schema changes; otherwise escalate.

Stage 5 — Downstream Pipeline Alignment (Fivetran)
- Input: `{collection_mod_metadata, target_delta_rules}`
- Actions:
  - Adjust connector mappings in Fivetran to tolerate the modified schema
  - Trigger on-demand resync and watch for connector health
- Output: resync status and connector logs

Stage 6 — Cognitive Integrity Assessment (Arize)
- Input: full execution trace + model prompts + token usage
- Actions:
  - Ingest telemetry and evaluate prompts for injection risk, token efficiency, and correctness
  - Produce a compliance and drift score
- Output: compliance report and suggested guardrail updates

Cross-Domain Data Handshake Matrix
---------------------------------
- Maintain a shared Pydantic model `Handshake` used to pass data between adapters. Example fields:
  - `origin_stage`, `service_id`, `pod_id`, `time_window`, `error_string`, `file_path`, `commit_sha`, `schema_patch`, `correlation_id`
- Always include `correlation_id` and `agent_id` for distributed tracing.

Testing Strategy
----------------
- Unit tests: validate each adapter's request/response normalization using sample JSON fixtures.
- Integration tests: spin up local mock MCP endpoints in `demo/mocks/` and run the Stage 1→3 flow end-to-end.
- E2E demo script: `demo/run_demo.py` simulates an incoming Dynatrace alert and advances through all stages, asserting final state.

Deployment & Operations
-----------------------
- Target runtime: Google Cloud Run (or Cloud Run for Anthos for VPC integration).
- Secrets: store partner credentials and API keys in Secret Manager; use Workload Identity.
- Scaling: Cloud Run instance concurrency tuned to expected throughput; set minInstances=1 for low-latency critical paths.
- Observability: Export OpenTelemetry traces and metrics; centralize logs to Cloud Logging; set alerting for failed heals or high retry counts.

Security & Governance
---------------------
- Use IAM and Workload Identity to map `agent_id` → service account.
- Sign and timestamp every mutating JSON-RPC request; persist signed audit trail.
- Model Armor enforces deny/allow policies; use an external policy engine (OPA) for complicated rules.

Developer Experience & CI/CD
---------------------------
- Provide `make` targets or `nox/pytest` tasks for local testing.
- Build container images with minimal base (distroless) and pinned dependencies.
- Add a GitHub/GitLab pipeline job to run integration tests against the `demo/mocks` environment.

Roadmap / Milestones
--------------------
1. Scaffolding: Central Orchestrator + Agent Gateway skeleton (week 1)
2. Mocks: local Dynatrace + Elastic mock endpoints + demo script (week 1–2)
3. Stage 1–3 prototype end-to-end with GitLab mock (week 2–3)
4. Add MongoDB/Fivetran adapters + safe mutation policies (week 3–4)
5. Arize integration + final compliance scoring & UI polish (week 4–5)
6. Production hardening and deployment guides (final week)

Files to Create (initial)
-------------------------
- `agent/orchestrator.py` — central workflow coordinator
- `agent/jsonrpc/client.py` — JSON-RPC client
- `agent/gateway/server.py` — FastAPI gateway
- `agent/mcp_adapters/dynatrace.py` — adapter skeleton
- `demo/mocks/dynatrace_mock.py` — simple webhook + query handlers
- `demo/run_demo.py` — scenario runner

UI / UX Design — SRE Control Cockpit (placeholder)
------------------------------------------------
This section is reserved for the judge-facing UI/UX designs and notes. Use this space to attach wireframes, design tokens, and interaction notes.

1) Overall layout
- Header: Project title, global status (System Health), MTTD / MTTR metrics
- Left rail: Stage nodes (Dynatrace, Elastic, GitLab, MongoDB, Fivetran, Arize) with live status dots
- Center: Topology grid — animated flow lines showing active remediation path
- Right panel: Detailed event trace for selected stage (logs, RPC payloads, agent decisions, MR link)

2) Visual language & tokens
- Palette: Dark-slate background (#0E1117), Crimson (#FF3B30) for critical, Amber for working, Emerald for success
- Typography: Clear mono for logs (e.g., JetBrains Mono) and readable sans for UI (e.g., Inter)

3) Interactive elements
- Expandable timeline: show each RPC call, start/end times, delta durations
- Approve / reject toggle for inline safety interventions (for judges to simulate human-in-loop)
- Re-run step button to replay a stage with modified parameters

4) Mockups and assets
- Add Figma links or screenshots here (placeholder)

5) Accessibility & Presentation Notes
- High contrast states for judge readability, keyboard navigation for key interactions, and an explainer overlay for the judging video.

Next steps
----------
- If you want, I will scaffold the initial files: `agent/jsonrpc/client.py`, `agent/orchestrator.py`, and `demo/mocks/dynatrace_mock.py` and run the Stage 1→2 unit demo locally.

Appendix — Example JSON-RPC request/response
-------------------------------------------
Request:

{
  "jsonrpc": "2.0",
  "id": "1d2f3a4b-...",
  "method": "mcp.exec",
  "params": {
    "action": "query_topology",
    "payload": {"service": "payments", "time_window": "2026-06-09T10:00:00Z/2026-06-09T10:02:00Z"},
    "agent_id": "agent-0a1b2c"
  }
}

Response (success):

{
  "jsonrpc": "2.0",
  "id": "1d2f3a4b-...",
  "result": {
    "service_id": "svc-payments",
    "pod_id": "k8s-pod-x92-node4",
    "container_signature": "sha256:..."
  }
}
