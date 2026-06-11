# Track 6: Elastic — WIN Proof

## Judging Criteria: Agent Builder + ES|QL Tools + Context Layer + Hybrid Search

### What We Built

Elastic is SENTINEL’s long-term memory and intelligence layer. Every incident is written back to Elasticsearch as enriched intelligence — not raw event data. The agent retrieves this memory before every healing operation, getting smarter with every incident.

### 1. Elastic Agent Builder + MCP Server (Primary — WIN Condition)

**File:** `agent/.adk/config.json`

```json
"elastic": {
  "command": "npx",
  "args": ["-y", "@elastic/mcp-server-elasticsearch"],
  "env": {
    "ES_URL": "${ELASTIC_ENDPOINT}",
    "ES_API_KEY": "${ELASTIC_API_KEY}"
  }
}
```

### 2. Four ES|QL Custom Tools (Paste into Agent Builder → Kibana UI)

**File:** `agent/tools/elastic_memory.py` — see `SEARCH_ESQL`, `STATS_ESQL`, `RISK_ESQL`, `PATCH_HISTORY_ESQL`

| Tool | ES|QL Purpose |
|---|---|
| `search_sentinel_history` | Retrieve past incidents for a collection |
| `get_escalation_stats` | Aggregate containment + escalation rates |
| `find_collections_at_risk` | Identify collections with 2+ escalations |
| `get_patch_strategy_history` | Retrieve proven patch strategies |

Agent Builder exposes these as MCP tools automatically — no proxy, no wrapper.

### 3. Context Layer (Elastic’s Core Requirement)

`index_incident_report()` writes the agent’s own enriched interpretation back to ES after every run:

```python
# NOT raw event data:
# {"timestamp": "...", "doc_id": "...", "error": "..."}

# Agent-generated intelligence:
{
  "insight": "Collection 'orders' experienced 3 schema violations. "
              "Resolution: CONTAINED. Patch: make_optional on amount field. "
              "2 documents quarantined.",
  "collection_name": "orders",
  "final_status": "CONTAINED",
  ...
}
```

Raw signals become retrievable intelligence. The `insight` field is what future runs search against.

### 4. ELSER Hybrid Search (Semantic + Keyword)

`search_incident_history()` combines:
- **BM25** keyword match on the `insight` field
- **ELSER sparse vector** semantic match — finds violations described differently but semantically related
- **Boost** for `CONTAINED` outcomes — proven strategies surface first

### 5. Agent Builds on What It Knows

Before patching, SENTINEL calls `get_patch_strategy_history(collection_name)` to find previously successful strategies for that collection. It reuses proven approaches rather than reasoning from scratch — getting faster and more accurate with every incident.

### Setup

See [`docs/elastic_agent_builder_setup.md`](docs/elastic_agent_builder_setup.md) for the complete 6-step guide.

---

*SENTINEL · Elastic Track · Google Cloud Rapid Agent Hackathon 2026*
