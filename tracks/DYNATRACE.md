# Track 3: Dynatrace — WIN Proof

## Judging Criteria: AI Observability + OTel Integration + Production KPIs

### What We Built

SENTINEL exports full OpenTelemetry traces to Dynatrace with SENTINEL-specific semantic attributes — not just generic LLM spans, but production-grade database incident KPIs.

### 1. Dual OTel Export (Arize + Dynatrace simultaneously)

**File:** `agent/observability.py`

A single `BatchSpanProcessor` sends spans to both:
- **Arize Phoenix** — for evals and self-improvement
- **Dynatrace OTLP endpoint** — for production dashboards

No double-instrumentation. One tracer provider, two exporters.

### 2. SENTINEL-Specific Span Attributes (WIN Condition)

Every SENTINEL tool call is wrapped in `sentinel_span()`, which attaches:

| Attribute | Type | Example |
|---|---|---|
| `sentinel.tool_name` | string | `"patch_collection_schema"` |
| `sentinel.collection_name` | string | `"orders"` |
| `sentinel.violation_count` | int | `3` |
| `sentinel.patch_strategy` | string | `"make_optional"` |
| `sentinel.resolution_status` | string | `"CONTAINED"` |
| `sentinel.quarantine_count` | int | `2` |

Dynatrace dashboards can filter and alert on these attributes:
- Alert when `sentinel.resolution_status = ESCALATE`
- Chart `sentinel.violation_count` over time by collection
- SLO on `sentinel.resolution_status = CONTAINED` rate

### 3. Usage

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

### 4. Setup

```bash
export DYNATRACE_ENDPOINT=https://<env-id>.live.dynatrace.com/api/v2/otlp
export DYNATRACE_TOKEN=dt0c01.<your-token>

# SENTINEL auto-configures on startup — no code changes needed
python -m agent.main orders
```

---

*SENTINEL · Dynatrace Track · Google Cloud Rapid Agent Hackathon 2026*
