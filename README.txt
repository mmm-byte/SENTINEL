# 🛡️ SENTINEL — MongoDB Schema Continuity Agent

> **An autonomous AI agent that detects, contains, and reports schema violations in real-time — without interrupting live application traffic.**

[![Google Cloud](https://img.shields.io/badge/Google%20Cloud-ADK%20%2B%20Gemini-4285F4?logo=googlecloud)](https://cloud.google.com/)
[![MongoDB](https://img.shields.io/badge/MongoDB-MCP%20Server-47A248?logo=mongodb)](https://www.mongodb.com/)
[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?logo=python)](https://python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

**Google Cloud Rapid Agent Hackathon 2026 · MongoDB Partner Track**

---

## 🎯 The Problem

When an application deployment ships a bad schema change, your MongoDB collection doesn't crash immediately — it silently ingests corrupt data. Documents arrive missing required fields. Type mismatches accumulate. By the time a human DBA investigates, thousands of malformed records have polluted production.

Manual remediation under live traffic is a high-stakes bottleneck:
- You can't drop the validator (breaks new writes)
- You can't stop the application (SLA breach)
- You can't migrate manually fast enough

**SENTINEL solves this autonomously in under 60 seconds.**

---

## 🤖 What SENTINEL Does

SENTINEL is a **5-step autonomous pipeline** that activates the moment a schema alert fires:

```
 ALERT RECEIVED
      │
      ▼
┌─────────────────────────────────────────────────────────────┐
│  Step 1: INSPECT                                            │
│  Reads the live $jsonSchema validator from the collection   │
│  Extracts required fields, property types, constraints      │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│  Step 2: VALIDATE                                           │
│  Checks incoming payload against the extracted schema       │
│  Classifies violations: MISSING_REQUIRED_FIELD / TYPE_MISMATCH │
│  Assigns severity: OK / WARNING / CRITICAL                  │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│  Step 3: PATCH                                              │
│  Surgically relaxes the schema using collMod                │
│  Removes only the violating fields from 'required'          │
│  Adds new field definitions to 'properties' if needed       │
│  Sets validationLevel: "moderate" — live traffic CONTINUES  │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│  Step 4: QUARANTINE                                         │
│  Moves corrupt documents to {collection}_quarantine         │
│  Full _sentinel_metadata audit trail preserved              │
│  Source document deleted only AFTER successful quarantine   │
│  Zero data loss — documents remain recoverable              │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│  Step 5: REPORT                                             │
│  Generates structured incident report with:                 │
│    • Executive summary for stakeholders                     │
│    • Full pipeline trace for engineers                      │
│    • Actionable next_actions checklist                      │
│    • Status: CONTAINED / ESCALATE / RESOLVED                │
└─────────────────────────────────────────────────────────────┘
```

---

## 🏗️ Architecture

### Layer 1 (Built): SENTINEL MongoDB Agent

```
┌──────────────────────────────────────────────────────────┐
│                    SENTINEL AGENT                        │
│              google.adk.agents.LlmAgent                  │
│              Model: Gemini 2.0 Flash                     │
│                                                          │
│  ┌─────────────────────────────────────────────────┐    │
│  │          MongoDB MCP Server (stdio)              │    │
│  │       @mongodb-js/mongodb-mcp-server             │    │
│  │  • list_collections   • find   • aggregate       │    │
│  │  • insert_one         • update • run_command      │    │
│  └─────────────────────────────────────────────────┘    │
│                                                          │
│  Custom Tool Pipeline:                                   │
│  [inspect_schema] → [validate_payload]                   │
│       → [patch_schema] → [quarantine_docs]               │
│                → [generate_report]                       │
└──────────────────────────────────────────────────────────┘
         │
         ▼
  MongoDB Atlas Cluster
  (sentinel_demo database)
```

### Layer 2 (Vision): Cross-Domain Self-Healing Orchestrator

```
                 ┌──────────────────────────────────┐
                 │    ARIZE SUPERVISOR AGENT         │
                 │   Real-time cognitive trace       │
                 │   drift monitor watching ALL      │
                 │   sub-agents for loops / halluc.  │
                 └──────────────┬───────────────────┘
                                │
                    Routes by alert_type
          ┌─────────────────────┼─────────────────────┐
          │                     │                     │
    ELASTIC AGENT         GITLAB AGENT         MONGODB AGENT ✅
    Log Triage &         Code Rollback &      Schema Continuity
    Root-Cause           Regression            (THIS SUBMISSION)
    Synthesis            Isolation
          │                     │                     │
          └─────────────────────┴─────────────────────┘
                                │
                         FIVETRAN AGENT
                    Autonomous Pipeline Healer
                    (Re-aligns data warehouse
                     after schema drift)
```

> **Note:** Only the MongoDB SENTINEL agent is fully implemented in this submission.  
> The `orchestrator/master_agent.py` file shows how all 5 partner agents would  
> compose into the complete self-healing architecture.

---

## ⚡ Quick Start

### Prerequisites

- Python 3.11+
- Node.js 18+ (for MongoDB MCP server)
- A free [MongoDB Atlas](https://www.mongodb.com/atlas) cluster
- A Google Cloud project with Gemini API enabled

### 1 — Clone & Install

```bash
git clone https://github.com/YOUR_USERNAME/sentinel-agent.git
cd sentinel-agent

pip install -r requirements.txt
npm install -g @mongodb-js/mongodb-mcp-server
```

### 2 — Configure Environment

```bash
cp .env.example .env
```

Edit `.env`:

```dotenv
MONGODB_CONNECTION_STRING=mongodb+srv://<user>:<pass>@<cluster>.mongodb.net/
MONGODB_DATABASE=sentinel_demo
GEMINI_MODEL=gemini-2.0-flash-exp
GOOGLE_CLOUD_PROJECT=your-project-id
GOOGLE_CLOUD_LOCATION=us-central1
GOOGLE_API_KEY=your-gemini-api-key
```

### 3 — Seed the Demo Database

```bash
# Create the 'orders' collection with strict $jsonSchema validator
python -m demo.setup_demo_collection

# Inject corrupt documents to trigger SENTINEL
python -m demo.inject_schema_drift
```

### 4 — Run SENTINEL

**Option A — ADK Web UI (Recommended for demo)**
```bash
adk web
# Visit http://localhost:8000
# Select "sentinel_agent" from the dropdown
# Paste the system alert text and watch SENTINEL execute
```

**Option B — CLI runner**
```bash
python -m demo.run_demo
```

---

## 🎬 Demo Walkthrough

The demo simulates a bad deployment that ships two malformed order documents:

| Document | Violation | Severity |
|---|---|---|
| ORD-99999 | `order_id` is integer (expected string); `amount` field missing | CRITICAL |
| ORD-88888 | `amount` is string "free" (expected double) | CRITICAL |

**What SENTINEL does in response:**

1. **INSPECT** — Reads the $jsonSchema validator: 5 required fields, `amount` must be `double`
2. **VALIDATE** — Confirms 3 violations across 2 documents: 1× MISSING_REQUIRED_FIELD + 2× TYPE_MISMATCH
3. **PATCH** — Issues `collMod` to relax `amount` from required; sets `validationLevel: moderate`; live traffic continues uninterrupted
4. **QUARANTINE** — Moves both corrupt documents to `orders_quarantine` with full audit metadata
5. **REPORT** — Generates structured incident report: `status: CONTAINED`, next_actions include DBA review of quarantine + permanent schema fix

**Total pipeline execution: < 60 seconds**

---

## 🧪 Tests

```bash
pytest tests/ -v
```

Tests cover all 5 pipeline tools with mock MongoDB — no Atlas connection required.

---

## 📦 Project Structure

```
sentinel-agent/
├── agent/
│   ├── main.py                  ← Core ADK agent + MCP integration
│   ├── config.py                ← Environment configuration
│   └── tools/
│       ├── schema_inspector.py  ← Step 1: INSPECT
│       ├── payload_validator.py ← Step 2: VALIDATE
│       ├── schema_patcher.py    ← Step 3: PATCH
│       ├── quarantine_manager.py← Step 4: QUARANTINE
│       └── incident_reporter.py ← Step 5: REPORT
├── orchestrator/
│   └── master_agent.py          ← Layer 2: Cross-domain vision
├── demo/
│   ├── setup_demo_collection.py ← Create Atlas demo data
│   ├── inject_schema_drift.py   ← Simulate bad deployment
│   └── run_demo.py              ← One-command demo runner
├── tests/
│   └── test_tools.py            ← Unit tests (all 5 tools)
├── requirements.txt
├── .env.example
└── README.md
```

---

## 🛠️ Tech Stack

| Component | Technology |
|---|---|
| AI Reasoning Engine | Gemini 2.0 Flash (via Google AI API) |
| Agent Framework | Google ADK (`google-adk`) |
| Database Integration | MongoDB MCP Server (`@mongodb-js/mongodb-mcp-server`) |
| Database | MongoDB Atlas (free M0 tier) |
| Schema Operations | PyMongo `collMod`, `list_collections`, `$jsonSchema` |
| Deployment | Google Cloud Run (ADK-compatible) |
| Testing | Pytest + unittest.mock |
| CLI / UI | ADK Web (`adk web`) |

---

## 🏆 Judging Criteria Alignment

| Criterion | How SENTINEL Delivers |
|---|---|
| **Technical Implementation** | Full ADK agent with MCPToolset stdio integration; 5 distinct custom tools each calling real MongoDB operations; no hardcoded logic — Gemini reasons through each step |
| **Design** | Strict pipeline sequencing enforced via system instruction; quarantine shadow collection preserves data integrity; `collMod` chosen over schema drop to minimize blast radius |
| **Potential Impact** | Reduces DBA incident response from hours to <60 seconds; zero data loss guarantee; applicable to any MongoDB-backed production system |
| **Quality of Idea** | Schema drift under live traffic is a real, unsolved production pain point; SENTINEL addresses it end-to-end autonomously without human-in-the-loop for containment |

---

## 🔒 Design Principles

- **Zero data destruction** — Corrupt documents are quarantined, never deleted
- **Minimum blast radius** — Only the violating fields are relaxed; the rest of the schema stays strict
- **Always surgical** — Uses `collMod` + `validationLevel: moderate` instead of dropping the entire validator
- **Full audit trail** — Every quarantined document carries `_sentinel_metadata` with timestamp, violations, and remediation hint
- **Live traffic continuity** — Application writes never stop; SENTINEL operates in parallel

---

## 🌐 Cross-Domain Vision (Layer 2)

SENTINEL is the MongoDB node in a larger self-healing ecosystem. The full architecture (see `orchestrator/master_agent.py`) chains five partner-track agents:

| Agent | Partner | Responsibility |
|---|---|---|
| **Arize Supervisor** | Arize Phoenix | Watches all agents for hallucinations and infinite loops |
| **Elastic Log Agent** | Elastic | Synthesises root-cause from distributed log streams |
| **GitLab Rollback Agent** | GitLab | Isolates breaking diff and opens automated Merge Request |
| **SENTINEL** ← *this submission* | **MongoDB** | Patches schema and quarantines corrupt data |
| **Fivetran Pipeline Agent** | Fivetran | Re-aligns warehouse sync after upstream schema mutation |

When Elastic surfaces a root-cause log signature, it triggers the GitLab agent to roll back the bad commit — which in turn unblocks SENTINEL from applying the permanent schema fix — which finally lets Fivetran re-sync the clean data downstream. Full closed-loop remediation.

---

## 📄 License

MIT © 2026 — see [LICENSE](LICENSE)

---

*Built for the Google Cloud Rapid Agent Hackathon 2026 · MongoDB Partner Track*  
*Deadline: June 11, 2026 @ 4:00 PM CDT*
