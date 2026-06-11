# Track 4: Fivetran — WIN Proof

## Judging Criteria: Pipeline Automation + MCP Integration + Closed-Loop Healing

### What We Built

When SENTINEL heals a schema violation, the downstream data warehouse is automatically re-synced via Fivetran — without any human intervention. Clean data propagates end-to-end.

### 1. Fivetran MCP Server (Primary — WIN Condition)

**File:** `agent/.adk/config.json`

```json
"fivetran": {
  "command": "npx",
  "args": ["-y", "fivetran-mcp"],
  "env": {
    "FIVETRAN_API_KEY": "${FIVETRAN_API_KEY}",
    "FIVETRAN_API_SECRET": "${FIVETRAN_API_SECRET}"
  }
}
```

Gemini calls `fivetran_list_connectors` and `fivetran_sync_connector` as native MCP tools.

### 2. Dynamic Connector Discovery (No Hardcoded IDs)

**File:** `orchestrator/fivetran_agent.py`

The agent never uses a hardcoded connector ID:

```python
# Full decision chain:
connectors = list_fivetran_connectors()          # list all
connector_id = find_connector_for_collection("orders")  # match by schema name
trigger_fivetran_resync(connector_id)            # trigger sync
```

Matching logic: connector `schema` name containing the MongoDB collection name.
Fallback: first active connector in the account.

### 3. Closed-Loop Integration

The pipeline is complete:
```
MongoDB corrupt data → SENTINEL heals → Fivetran resyncs → warehouse is clean
```

No manual step. No Slack message. No ticket. Full autonomous closed loop.

### 4. Setup

```bash
npm install -g fivetran-mcp

export FIVETRAN_API_KEY=your_api_key
export FIVETRAN_API_SECRET=your_api_secret

# Fivetran resync triggers automatically after CONTAINED status
python -m agent.main orders
```

---

*SENTINEL · Fivetran Track · Google Cloud Rapid Agent Hackathon 2026*
