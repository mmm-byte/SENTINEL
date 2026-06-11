<!--
  SENTINEL — README
  Google Cloud Rapid Agent Hackathon 2026
  6 Partner Tracks · 1 Autonomous Agent
-->

<div align="center">

```
████████████████████████████████████████████████████████████████
██  ████████████████████████████████████████████████████████████  ██
██  ██  ████████████████████████████████████████████████████████  ██  ██
██  ██  ██          SENTINEL                        ██  ██  ██
██  ██  ██    The Autonomous Database                 ██  ██  ██
██  ██  ██    Immune System                          ██  ██  ██
██  ██  ████████████████████████████████████████████████████████  ██  ██
██  ████████████████████████████████████████████████████████████  ██
████████████████████████████████████████████████████████████████
```

# SENTINEL
### The Autonomous Database Immune System

**When a bad deployment poisons your MongoDB collection, SENTINEL detects it, contains it, and heals it — before a single human wakes up.**

<br>

[![Google ADK](https://img.shields.io/badge/Google%20ADK-Gemini%202.0%20Flash-4285F4?style=for-the-badge&logo=google&logoColor=white)](https://cloud.google.com/)
[![MongoDB Atlas](https://img.shields.io/badge/MongoDB-Atlas%20%2B%20Vector%20Search%20%2B%20Change%20Streams-47A248?style=for-the-badge&logo=mongodb&logoColor=white)](https://www.mongodb.com/)
[![Arize Phoenix](https://img.shields.io/badge/Arize-Phoenix%20%2B%20LLM%20Evals-FF6B35?style=for-the-badge)](https://phoenix.arize.com/)
[![Elastic](https://img.shields.io/badge/Elastic-Agent%20Builder%20%2B%20ES%7CQL-005571?style=for-the-badge&logo=elastic&logoColor=white)](https://elastic.co/)
[![Dynatrace](https://img.shields.io/badge/Dynatrace-OTel%20%2B%20AI%20Observability-1496FF?style=for-the-badge&logo=dynatrace&logoColor=white)](https://dynatrace.com/)
[![Fivetran](https://img.shields.io/badge/Fivetran-MCP%20%2B%20Auto--Resync-0073E6?style=for-the-badge)](https://fivetran.com/)
[![GitLab](https://img.shields.io/badge/GitLab-Duo%20Agent%20%2B%20MR%20Automation-FC6D26?style=for-the-badge&logo=gitlab&logoColor=white)](https://gitlab.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-22c55e?style=for-the-badge)](LICENSE)

<br>

> **Google Cloud Rapid Agent Hackathon 2026 · 6 Partner Tracks**

</div>

---

## The Problem No DBA Wants at 3 AM

A developer ships a routine feature. Buried in the diff: one field rename, one type change. The deployment succeeds. The monitoring dashboard shows green.

But MongoDB is now silently ingesting corrupt documents.

By the time an alert fires, **ten thousand malformed records** are in production. The DBA faces an impossible choice:
- Drop the validator → breaks new writes permanently
- Stop the application → SLA breach, revenue loss
- Manually migrate → takes hours, error-prone under pressure

**There is no good option. Until now.**

---

## SENTINEL’s Answer: The 5-Step Immune Response

The moment a corrupt document enters a monitored collection, SENTINEL fires a fully autonomous pipeline:

```
┌─────────────────────────────────────────────────────────────────────────┐
│                                                                       │
│   MongoDB Change Stream fires → SENTINEL wakes                       │
│                                                                       │
│   [1] INSPECT    Read live $jsonSchema validator from collection       │
│         ↓                                                             │
│   [2] VALIDATE   Check payload → classify MISSING_FIELD / TYPE_MISMATCH│
│         ↓                                                             │
│   [3] PATCH      collMod: relax only the violating fields              │
│                  validationLevel: moderate → live traffic continues   │
│         ↓                                                             │
│   [4] QUARANTINE Move corrupt docs to {collection}_quarantine          │
│                  Full _sentinel_metadata audit trail preserved         │
│         ↓                                                             │
│   [5] REPORT     Structured incident report → Elastic memory           │
│                  Fivetran resync triggered → GitLab MR opened          │
│                  Arize evals scored → agent self-improves              │
│                                                                       │
│   Total elapsed: < 60 seconds. Human involvement: 0.                  │
│                                                                       │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Architecture: 6-Partner Closed-Loop System

```
                    ┌───────────────────────────┐
                    │   MongoDB Change Stream    │
                    │   (always-on watcher)      │
                    └───────────┤──────────────┘
                                  │
                                  ▼
          ┌────────────────────────────────────────┐
          │          SENTINEL CORE AGENT                  │
          │    Google ADK · Gemini 2.0 Flash              │
          │                                               │
          │  MCP Servers wired (agent/.adk/config.json):   │
          │  ● MongoDB MCP  ● Phoenix MCP               │
          │  ● Fivetran MCP ● GitLab MCP                │
          │  ● Elastic MCP                              │
          └──────────────┬─────────────────────────┘
                           │
         ╒════════════╯═════════════════════════╒
         ║                                                  ║
         ║   After every incident, SENTINEL calls:          ║
         ║                                                  ║
    ┌────┴────┐  ┌──────┐  ┌────────┐  ┌────────┐  ┌───────┐
    │ ARIZE  │  │DYNA- │  │ELASTIC │  │FIVETRAN│  │GITLAB │
    │PHOENIX │  │TRACE │  │ Agent  │  │  MCP   │  │  Duo  │
    │Evals + │  │OTel  │  │Builder │  │Resync  │  │ Agent │
    │Self-   │  │Spans │  │ES|QL   │  │after   │  │ Open  │
    │Improve │  │KPIs  │  │Memory  │  │CONTAIN │  │ MR on │
    │  Loop  │  │      │  │+ELSER  │  │        │  │ESCL8  │
    └────────┘  └──────┘  └────────┘  └────────┘  └───────┘
         ║                                                  ║
         ╚══════════════════════════════════════════════════╝
```

> **This is not 6 isolated integrations. Every partner platform is a live part of one closed-loop autonomous system.**

---

## Partner Track Implementations

### 🍿 Track 1 — MongoDB
> *Unified operational + vector + streaming platform*

| Feature | Implementation |
|---|---|
| **5-step schema healing pipeline** | `agent/tools/` — inspect → validate → patch → quarantine → report |
| **MongoDB MCP Server** | `agent/.adk/config.json` — Gemini calls `find`, `aggregate`, `run_command` natively |
| **Atlas Vector Search** | `agent/tools/vector_search.py` — semantic incident recall with Google `text-embedding-004` |
| **Change Streams** | `agent/watcher.py` — always-on reactive trigger; SENTINEL fires the instant a corrupt doc arrives |
| **$jsonSchema patching** | Surgical `collMod` — only violating fields relaxed; zero blast radius |
| **Quarantine collection** | `{collection}_quarantine` with full `_sentinel_metadata` audit trail |

```bash
# Start the always-on watcher
python -m agent.watcher orders,users,payments
```

---

### 📊 Track 2 — Arize Phoenix
> *Production tracing + LLM-as-a-Judge + self-improvement loop*

| Feature | Implementation |
|---|---|
| **OpenInference tracing** | `agent/observability.py` — `GoogleADKInstrumentor` auto-traces every tool call |
| **Phoenix MCP Server** | `agent/.adk/config.json` — agent queries its own traces at runtime |
| **LLM-as-a-Judge evals** | `agent/evals.py` — Gemini judges every trace on 3 dimensions |
| **Self-improvement loop** | Low-scoring traces → `improvement_hint` → fed back into agent strategy |
| **Scores written to Phoenix** | `POST /v1/span_annotations` — visible in Phoenix Cloud dashboard |

Eval dimensions scored 0.0–1.0 per trace:
- `patch_minimality` — Was the schema change as surgical as possible?
- `violation_accuracy` — Were all violations correctly identified?
- `quarantine_correctness` — Were the right documents quarantined?

```python
from agent.evals import run_self_improvement_loop
result = run_self_improvement_loop(last_n_traces=10)
# → {"avg_overall_score": 0.91, "improvement_recommendations": [...]}
```

---

### 🔭 Track 3 — Dynatrace
> *Dual OTel export with SENTINEL-specific production KPIs*

| Feature | Implementation |
|---|---|
| **Dual OTel export** | Arize Phoenix + Dynatrace receive the same spans simultaneously |
| **Custom span attributes** | `sentinel_span()` context manager wraps every tool call |
| **SENTINEL-specific KPIs** | `sentinel.violation_count`, `sentinel.patch_strategy`, `sentinel.resolution_status`, `sentinel.quarantine_count` |
| **Zero-config fallback** | Module is a no-op if env vars absent — never breaks CI |

Dynatrace dashboards display SENTINEL-specific metrics — not just generic LLM spans:

```python
with sentinel_span(
    "patch_collection_schema",
    collection_name="orders",
    violation_count=3,
    patch_strategy="make_optional",
    resolution_status="CONTAINED",
    quarantine_count=2,
):
    result = patch_collection_schema(...)
```

---

### 🔄 Track 4 — Fivetran
> *MCP-native pipeline healer — clean data propagates downstream automatically*

| Feature | Implementation |
|---|---|
| **Fivetran MCP Server** | `agent/.adk/config.json` — Gemini calls `fivetran_sync_connector` natively |
| **Dynamic connector lookup** | `find_connector_for_collection()` — maps MongoDB collection → connector by schema name |
| **Auto-resync on CONTAINED** | Triggered automatically after successful schema healing |
| **REST fallback** | `orchestrator/fivetran_agent.py` for non-MCP environments |

The agent never uses a hardcoded connector ID:
1. `list_fivetran_connectors()` → discover all connectors
2. `find_connector_for_collection("orders")` → match by schema name
3. `trigger_fivetran_resync(connector_id)` → clean data flows downstream

---

### 🤖 Track 5 — GitLab
> *Duo Agent Platform registration + automated rollback MR on escalation*

| Feature | Implementation |
|---|---|
| **GitLab MCP Server** | `agent/.adk/config.json` — Gemini calls `create_merge_request` natively |
| **GitLab Duo Custom Agent** | `register_sentinel_as_duo_agent()` registers SENTINEL in GitLab AI Catalog |
| **Automated rollback MR** | Opens MR with full violation summary when `resolution_status=ESCALATE` |
| **Duo invocation hook** | MR template includes `/sentinel analyze-schema-break` Duo command |
| **REST fallback** | `orchestrator/gitlab_agent.py` for non-MCP environments |

SENTINEL is registered as a GitLab Duo Custom Skill — GitLab CI pipelines can invoke it when a schema-breaking commit appears in a merge request diff.

---

### 🔍 Track 6 — Elastic
> *Agent Builder + ES|QL custom tools + ELSER hybrid search + context layer memory*

| Feature | Implementation |
|---|---|
| **Elastic Agent Builder** | ES|QL tools defined in Kibana UI — exposed as native MCP tools |
| **Elastic MCP Server** | `agent/.adk/config.json` — `@elastic/mcp-server-elasticsearch` |
| **4 ES|QL custom tools** | `search_sentinel_history`, `get_escalation_stats`, `find_collections_at_risk`, `get_patch_strategy_history` |
| **Context layer (memory)** | `index_incident_report()` writes enriched agent insights back to ES after every run |
| **ELSER hybrid search** | `sparse_vector` + BM25 on `insight` field — semantic + keyword |
| **Agent builds on knowledge** | `get_patch_strategy_history()` retrieves proven fixes before reasoning from scratch |

See [`docs/elastic_agent_builder_setup.md`](docs/elastic_agent_builder_setup.md) for the full 6-step setup guide.

---

## Quick Start

### Prerequisites

- Python 3.11+
- Node.js 18+ (for MCP servers)
- [MongoDB Atlas](https://www.mongodb.com/atlas) free M0 cluster
- Google Cloud project with Gemini API enabled

### 1 — Clone & Install

```bash
git clone https://github.com/mmm-byte/SENTINEL.git
cd SENTINEL

pip install -r requirements.txt

# Install all 5 MCP servers
npm install -g @mongodb-js/mongodb-mcp-server
npm install -g @arizeai/phoenix-mcp
npm install -g fivetran-mcp
npm install -g @gitlab-org/gitlab-mcp-server
npm install -g @elastic/mcp-server-elasticsearch
```

### 2 — Configure Environment

```bash
cp .env.example .env
# Fill in your credentials (see .env.example for all variables)
```

### 3 — Seed the Demo

```bash
# Create 'orders' collection with strict $jsonSchema + inject corrupt documents
python -m demo.setup_demo_collection
python -m demo.inject_schema_drift
```

### 4A — Run SENTINEL (ADK Web UI — best for demo)

```bash
adk web
# Visit http://localhost:8000
# Select "sentinel" agent
# Paste any schema alert and watch the 5-step pipeline execute live
```

### 4B — Run Always-On Watcher (reactive mode)

```bash
# Terminal 1: start the watcher
python -m agent.watcher orders

# Terminal 2: inject a corrupt document
python -m demo.inject_schema_drift

# Watch SENTINEL auto-fire in Terminal 1
```

### 4C — Run Self-Improvement Loop (Arize evals)

```bash
python -c "from agent.evals import run_self_improvement_loop; import json; print(json.dumps(run_self_improvement_loop(), indent=2))"
```

---

## Demo Scenario

A deployment ships two corrupt order documents into production:

| Doc | Violation | Severity |
|---|---|---|
| `ORD-99999` | `order_id` is `int` (expected `string`); `amount` missing | CRITICAL |
| `ORD-88888` | `amount` is `"free"` (expected `double`) | CRITICAL |

**SENTINEL’s response:**

```
[00:00] 🚨 Change Stream fires — 2 corrupt documents detected
[00:03] 🔍 INSPECT: $jsonSchema read — 5 required fields, amount must be double
[00:08] ⚠️  VALIDATE: 3 violations — 1x MISSING_REQUIRED_FIELD, 2x TYPE_MISMATCH
[00:12] 🔧 PATCH: collMod applied — amount removed from required[], validationLevel=moderate
           Live traffic: UNINTERRUPTED
[00:18] 📳 QUARANTINE: ORD-99999 → orders_quarantine (with audit metadata)
[00:19] 📳 QUARANTINE: ORD-88888 → orders_quarantine (with audit metadata)
[00:22] 📊 ELASTIC: Incident indexed — insight written to context layer
[00:24] 🔄 FIVETRAN: Connector matched 'orders_schema' → resync triggered
[00:28] 📝 REPORT: status=CONTAINED, next_actions=[3 items]
[00:30] 🧠 ARIZE EVALS: patch_minimality=0.95, violation_accuracy=1.0, quarantine=1.0

Total elapsed: 30 seconds. Human involvement: 0.
```

---

## Project Structure

```
SENTINEL/
├── agent/
│   ├── main.py                    ← Core ADK agent + all 5 MCP integrations
│   ├── evals.py                   ← Arize LLM-as-a-Judge + self-improvement loop
│   ├── observability.py           ← Dual OTel: Arize Phoenix + Dynatrace
│   ├── watcher.py                 ← MongoDB Change Stream — always-on trigger
│   ├── .adk/
│   │   └── config.json             ← 5 MCP servers: MongoDB, Phoenix, Fivetran, GitLab, Elastic
│   └── tools/
│       ├── schema_inspector.py     ← Step 1: INSPECT
│       ├── payload_validator.py    ← Step 2: VALIDATE
│       ├── schema_patcher.py       ← Step 3: PATCH
│       ├── quarantine_manager.py   ← Step 4: QUARANTINE
│       ├── incident_reporter.py    ← Step 5: REPORT
│       ├── elastic_memory.py       ← Track 6: Elastic context layer + ES|QL tools
│       └── vector_search.py        ← Track 1: MongoDB Atlas Vector Search
├── orchestrator/
│   ├── master_agent.py            ← Cross-domain vision: 5-agent orchestration
│   ├── fivetran_agent.py          ← Track 4: Fivetran MCP + REST fallback
│   └── gitlab_agent.py            ← Track 5: GitLab MCP + Duo Agent registration
├── demo/
│   ├── setup_demo_collection.py   ← Create Atlas demo data
│   ├── inject_schema_drift.py     ← Simulate bad deployment
│   └── run_demo.py                ← Full end-to-end demo runner
├── docs/
│   └── elastic_agent_builder_setup.md  ← Elastic Track 6 setup guide
├── tests/
│   └── test_tools.py              ← Unit tests: all 5 pipeline tools
├── requirements.txt               ← All deps, organized by track
└── .env.example                   ← All env vars for all 6 tracks
```

---

## Design Principles

**Zero data destruction.** Corrupt documents are quarantined, never deleted. Every document in `{collection}_quarantine` carries full `_sentinel_metadata`: timestamp, violations found, remediation hint, and the SENTINEL incident ID.

**Minimum blast radius.** SENTINEL relaxes only the specific fields causing violations. The rest of the `$jsonSchema` stays strict. A single missing field does not open the entire validator.

**Always surgical.** `collMod` + `validationLevel: moderate` — not `validationLevel: off`. The collection immediately re-validates compliant documents.

**Live traffic continuity.** Application writes never stop. SENTINEL operates in a parallel ADK execution context. The pipeline step sequence is enforced via system instruction — the agent cannot skip quarantine before patching.

**Self-improving.** After every 10 incidents, `run_self_improvement_loop()` pulls traces from Arize, scores them with Gemini-as-judge, and writes improvement hints back to Phoenix. SENTINEL gets measurably better the more it runs.

**Semantically aware.** Before patching, SENTINEL queries Elastic for past incidents with similar violation patterns (ELSER hybrid search) and Atlas Vector Search for semantically related historical incidents. It reuses proven strategies rather than reasoning from scratch every time.

---

## Tech Stack

| Layer | Technology |
|---|---|
| AI Reasoning | Gemini 2.0 Flash · Google ADK |
| Database | MongoDB Atlas (operational + vector + streaming) |
| Tracing & Evals | Arize Phoenix Cloud · OpenInference |
| Observability | Dynatrace · OpenTelemetry |
| Search & Memory | Elastic Agent Builder · ELSER · ES|QL |
| Pipeline Sync | Fivetran MCP |
| Code Ops | GitLab Duo Agent Platform |
| Runtime | Google Cloud Run · Python 3.11 |

---

## Tests

```bash
pytest tests/ -v
# All 5 pipeline tools tested with mock MongoDB — no Atlas connection required
```

---

## License

MIT © 2026 — see [LICENSE](LICENSE)

---

<div align="center">

**Built for the Google Cloud Rapid Agent Hackathon 2026**

*MongoDB · Arize · Dynatrace · Fivetran · GitLab · Elastic*

*6 tracks. 1 agent. 0 humans paged at 3 AM.*

</div>
