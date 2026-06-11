# Track 1: MongoDB — WIN Proof

## Judging Criteria: Technical Implementation + Real-World Impact

### What We Built

SENTINEL uses MongoDB Atlas as the **unified operational + vector + streaming** platform — no external database, no separate vector store, no separate message queue. One Atlas cluster does everything.

### 1. MongoDB MCP Server (Primary Integration)

`agent/.adk/config.json` wires `@mongodb-js/mongodb-mcp-server` via stdio.
Gemini calls MongoDB operations as native MCP tools:
- `find` — read documents for validation
- `aggregate` — run $jsonSchema inspection pipeline  
- `run_command` — execute `collMod` for schema patching
- `insert_one` — write quarantine documents

### 2. Atlas Vector Search (Semantic Incident Memory)

**File:** `agent/tools/vector_search.py`

- `semantic_incident_search(violation_description)` — finds past incidents with similar violation patterns using Google `text-embedding-004` + Atlas Vector Search
- `store_incident_with_embedding(report)` — stores every incident with its vector embedding for future recall
- Index: `sentinel_vector_index` on `sentinel_incidents.embedding` (cosine, 2048-dim)

This means SENTINEL gets smarter over time. A violation in `payments` that resembles a past `orders` incident retrieves the proven remediation strategy.

### 3. MongoDB Change Streams (Always-On Reactive Trigger)

**File:** `agent/watcher.py`

SENTINEL is not a tool-you-invoke. It is an immune system:
```bash
python -m agent.watcher orders,users,payments
```
Change Streams watch for `insert`, `update`, and `replace` events. The moment a corrupt document arrives, the full 5-step pipeline fires. No polling. No cron job. Zero latency.

### 4. $jsonSchema Surgical Patching

**File:** `agent/tools/schema_patcher.py`

- Reads the live validator via `listCollections`
- Removes only the violating field from `required[]`
- Sets `validationLevel: moderate` (not `off`)
- Live application writes continue uninterrupted

### 5. Zero Data Loss Quarantine

**File:** `agent/tools/quarantine_manager.py`

- Corrupt documents moved to `{collection}_quarantine`
- Source document deleted only AFTER quarantine insertion confirmed
- Every quarantined document carries `_sentinel_metadata`: timestamp, violations, incident ID, remediation hint

---

## Atlas Vector Search Index (Create Once)

```javascript
// mongosh — run in Atlas console
db.sentinel_incidents.createSearchIndex(
  "sentinel_vector_index",
  "vectorSearch",
  {
    fields: [{
      type: "vector",
      path: "embedding",
      numDimensions: 768,
      similarity: "cosine"
    }]
  }
);
```

---

*SENTINEL · MongoDB Track · Google Cloud Rapid Agent Hackathon 2026*
