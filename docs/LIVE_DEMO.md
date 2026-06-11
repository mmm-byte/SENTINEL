# SENTINEL · Live Demo Instructions

> How to run the SRE Control Cockpit and experience the full 6-stage self-healing flow.

## Setup (5 minutes)

```bash
# 1. Clone and enter the repo
git clone <repo-url> sentinel
cd sentinel

# 2. Install dependencies
pip install -r requirements.txt

# 3. Activate the virtual environment (optional if using pip)
python -m venv .venv && source .venv/bin/activate

# 4. Verify tests pass (smoke test)
pytest -q
# Expected: 36 passed in ~10s
```

## Run the Live Cockpit (2 minutes)

The SRE Control Cockpit is a **zero-dependency** web UI that works with no cloud credentials.

```bash
# Start the cockpit server
python -m agent.ui_server

# Open in browser
open http://127.0.0.1:8080

# (or visit http://localhost:8080 in your browser)
```

You should see:
- **Header** with "SENTINEL · SRE Control Cockpit" and "Mode: MOCK"
- **Left panel** with six colored stage boxes (Dynatrace, Elastic, GitLab, MongoDB, Fivetran, Arize)
- **Center panel** with a live "Live Audit & Trace" pre-log and metrics (MTTD, MTTR, Compliance)
- **Right panel** listing the six partner integrations and their use cases

## Trigger a Healing Run (30 seconds)

In the cockpit web page:

1. Click the **▶ Trigger Healing Run** button
   - The system starts a mock 6-stage healing simulation
   - You should see stages advance from idle → running → success
   
2. Watch the trace log update in real-time
   - Each line shows a timestamp and which stage is running

3. When you see the **⚠ awaiting approval** message for Stage 4 (MongoDB schema change):
   - The system paused because a destructive schema modification is pending
   - An approval box appears on the left: *"Awaiting human approval for stage4_db_stabilize: MongoDB collMod requested"*

4. Click **✓ Approve** to allow the schema change:
   - Stages 5 and 6 run
   - The run completes with final metrics: MTTR (total time), Compliance score

5. Once finished, metrics appear:
   - **MTTD**: 0.42s (mean time to detect)
   - **MTTR**: ~4.5s (mean time to repair)
   - **Compliance**: 97%

## Optional: Run the Full Workflow Demo

To run the same flow via CLI (without the web UI):

```bash
python -m demo.run_full_demo

# Expected output:
# [orchestrator] Running full 6-stage self-healing loop
# [orchestrator] done — correlation_id=<UUID>
# [orchestrator] final compliance=0.97 drift=0.03
# [orchestrator] audit trail entries: 12
```

## Under the Hood: What SENTINEL Does

### Stage 1: Dynatrace (Intake & Isolate)
- **What**: Receives an alert, maps it to a service and pod
- **Outcome**: Isolation token for later stages

### Stage 2: Elastic (Triage Logs)
- **What**: Queries Elastic for logs in the time window, extracts error signatures
- **Outcome**: Canonical error string and source file path

### Stage 3: GitLab (Remediate Code)
- **What**: Runs blame to find the suspicious commit, opens a hotfix branch + MR
- **Outcome**: A merge request with audit context

### Stage 4: MongoDB (DB Stabilize) ⭐ HERO STAGE
- **What**: Relaxes the schema validator, quarantines bad documents
- **Requires**: Human approval for destructive changes
- **Outcome**: Schema is now tolerant; bad docs are safe-kept

### Stage 5: Fivetran (Reconnect Pipeline)
- **What**: Adjusts connector mapping and triggers resync
- **Outcome**: Data warehouse catches up

### Stage 6: Arize (Cognitive Assess)
- **What**: Scores the remediation trace for drift and compliance
- **Outcome**: Compliance report + guardrail suggestions

## Inspecting the Code

After running the demo, inspect key files:

- `agent/orchestrator.py` — 6-stage orchestration engine
- `agent/model_armor.py` — safety policy enforcement (pre/post send)
- `agent/jsonrpc/client.py` — signed JSON-RPC with audit logging
- `agent/schemas/handshake.py` — the shared context object that threads through all stages
- `agent/mock_orchestrator.py` — the mock that drives the cockpit
- `ui/cockpit/index.html` — the SRE cockpit web page (no build, single HTML file)

## Security Features (Visible in Audit Log)

1. **Model Armor**: Every payload is inspected for size, dangerous keywords, prompt injection patterns
2. **Signed JSON-RPC**: Every call is HMAC-SHA256 signed (you can see the `signature` in audit events)
3. **Audit Trail**: Every action is logged in JSONL format (`./sentinel_audit.jsonl`)
4. **Human-in-the-Loop**: Stage 4 (schema changes) requires explicit approval

To inspect the audit log after a run:

```bash
cat sentinel_audit.jsonl | python -m json.tool | head -50
```

## Publishing Track-Specific Repos

To generate a clean, track-specific repository for submission:

```bash
# Generate a MongoDB track (hero track)
python scripts/publish_track.py --track mongodb --out /tmp/sentinel-mongodb

# Generate an Arize track (cognitive assessment)
python scripts/publish_track.py --track arize --out /tmp/sentinel-arize

# Other tracks: elastic, fivetran, gitlab, dynatrace
```

Each generated repo has:
- A unique README highlighting the partner's use case
- The full shared core (agent/, demo/, tests/, docs/)
- A track-specific `.env.example` with partner-specific secrets
- The SRE cockpit UI (ui/cockpit/)
- The publish script is removed (clean submission)

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Port 8080 in use | Use `python -m agent.ui_server --host 127.0.0.1 --port 9000` |
| Tests fail | Run `pytest -xvs tests/test_security.py` to debug |
| UI doesn't update | Refresh the browser or check console for errors (F12) |
| Stages stuck on "running" | The mock thread may have crashed; restart the server |

## Notes for Judges

- **Total setup time**: ~5 minutes
- **Demo runtime**: ~30 seconds per run
- **Repeatability**: Can run as many times as desired (just click "Trigger" again)
- **No secrets required**: The mock mode requires zero API keys
- **Live APIs**: When credentials are present, the system switches to live partner calls without code changes
- **Transparency**: All decisions are auditable: inspect `sentinel_audit.jsonl` for the full trace

---

**Shortcut: One-command startup**

```bash
cd /path/to/sentinel && source .venv/bin/activate && pytest -q && python -m agent.ui_server
# Then: open http://127.0.0.1:8080 and click "Trigger Healing Run"
```
