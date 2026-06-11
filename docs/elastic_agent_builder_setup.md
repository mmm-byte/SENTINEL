# Elastic Agent Builder Setup — Track 6 WIN

## Overview

SENTINEL integrates with Elastic via two layers:
1. **Elastic Agent Builder MCP Server** — exposes ES|QL tools natively to Gemini
2. **Python SDK fallback** — `agent/tools/elastic_memory.py` for non-MCP environments

---

## Step 1: Create Elastic Cloud Serverless Project

1. Sign up at [cloud.elastic.co](https://cloud.elastic.co) — free trial
2. Create a **Serverless Elasticsearch** project
3. Choose a Google Cloud region (us-central1 recommended)
4. Note your endpoint: `https://<deployment>.es.<region>.aws.elastic.cloud`

---

## Step 2: Enable Agent Builder in Kibana

1. Open Kibana from your Serverless project
2. Navigate to **Search > Agent Builder**
3. Click **Enable Agent Builder**
4. Agent Builder ships with a built-in MCP server — no extra config needed

---

## Step 3: Create ES|QL Custom Tools

In Agent Builder > **Tools** tab, create four tools by pasting these ES|QL queries:

### Tool 1: `search_sentinel_history`
**Description:** Retrieve past SENTINEL incidents for a MongoDB collection
**Parameter:** `collection_name` (string)
```esql
FROM sentinel_incidents
| WHERE collection_name == ?collection_name
| SORT timestamp DESC
| LIMIT 5
| KEEP incident_id, collection_name, final_status, violations_detected,
        documents_quarantined, schema_patched, insight, executive_summary, timestamp
```

### Tool 2: `get_escalation_stats`
**Description:** Get aggregate SENTINEL statistics across all collections
**No parameters**
```esql
FROM sentinel_incidents
| STATS
    total_incidents   = COUNT(),
    total_violations  = SUM(violations_detected),
    total_quarantined = SUM(documents_quarantined),
    escalations       = COUNT(*) WHERE final_status == "ESCALATE",
    contained         = COUNT(*) WHERE final_status == "CONTAINED"
| EVAL containment_rate = ROUND(contained / total_incidents * 100, 1)
```

### Tool 3: `find_collections_at_risk`
**Description:** Find collections with 2+ repeated escalations needing engineering attention
**No parameters**
```esql
FROM sentinel_incidents
| WHERE final_status == "ESCALATE"
| STATS escalation_count = COUNT() BY collection_name
| WHERE escalation_count >= 2
| SORT escalation_count DESC
| RENAME collection_name AS at_risk_collection
```

### Tool 4: `get_patch_strategy_history`
**Description:** Find proven patch strategies for a collection to avoid re-reasoning
**Parameter:** `collection_name` (string)
```esql
FROM sentinel_incidents
| WHERE collection_name == ?collection_name AND schema_patched == true
| SORT timestamp DESC
| LIMIT 10
| KEEP incident_id, collection_name, patch_summary, violations_detected, timestamp
```

---

## Step 4: Connect to Google Cloud Agent Builder via MCP

1. In Agent Builder > **Tools** tab, copy the **MCP Server Endpoint URL**
2. Copy your **Elasticsearch API Key** from Kibana > Stack Management > API Keys
3. In your Google Cloud Agent Builder config, add the Elastic MCP server:

```json
{
  "mcpServer": {
    "endpoint": "<MCP endpoint URL from Kibana>",
    "headers": {
      "Authorization": "ApiKey <your-api-key>"
    }
  }
}
```

The MCP config in `agent/.adk/config.json` also wires the
`@elastic/mcp-server-elasticsearch` package directly.

---

## Step 5: Set Environment Variables

Add to `.env`:
```bash
ELASTIC_ENDPOINT=https://<deployment>.es.<region>.aws.elastic.cloud
ELASTIC_API_KEY=<base64-encoded-api-key-from-kibana>
```

---

## Step 6: Load Demo Data

Run SENTINEL end-to-end once to populate the index:
```bash
python -m agent.main orders
```

Or seed directly:
```bash
python -c "
from agent.tools.elastic_memory import index_incident_report
index_incident_report({
    'incident_id': 'INC-DEMO-001',
    'collection_name': 'orders',
    'database_name': 'sentinel_demo',
    'final_status': 'CONTAINED',
    'violations_detected': 3,
    'documents_quarantined': 2,
    'schema_patched': True,
    'timestamp': '2026-06-10T22:00:00Z',
    'executive_summary': 'Three orders failed required field validation. Patch applied.',
    'next_actions': ['Monitor for 24h', 'Notify upstream producer'],
})
print('Seeded.')
"
```

---

## What This Demonstrates to Elastic Judges

| Elastic Criterion | SENTINEL Implementation |
|---|---|
| Elastic index as context layer | `index_incident_report()` writes enriched agent insights (not raw data) back to ES after every run |
| ES|QL custom tools | 4 tools in Agent Builder UI backed by ES|QL queries |
| MCP server | `@elastic/mcp-server-elasticsearch` in `.adk/config.json` |
| Hybrid semantic + keyword search | `search_incident_history()` combines BM25 + ELSER sparse_vector |
| Agent builds on what it knows | `get_patch_strategy_history()` reuses proven fixes |
| Subagent orchestration | SENTINEL calls Fivetran + GitLab agents after ES memory lookup |

---

*SENTINEL · Google Cloud Rapid Agent Hackathon 2026*
