# Track 2: Arize Phoenix — WIN Proof

## Judging Criteria: Technical Implementation + MCP + Self-Improvement Loop + Evals

### What We Built

SENTINEL doesn’t just run — it watches itself run, judges its own decisions, and gets better over time.

### 1. OpenInference Tracing (Technical Implementation)

**File:** `agent/observability.py`

```python
from phoenix.otel import register
from openinference.instrumentation.google_adk import GoogleADKInstrumentor

tracer_provider = register(project_name="sentinel", ...)
GoogleADKInstrumentor().instrument(tracer_provider=tracer_provider)
```

Every tool call, LLM invocation, and decision is automatically traced. Phoenix Cloud receives full spans for every SENTINEL run.

### 2. Phoenix MCP Server (Meaningful MCP Use)

**File:** `agent/.adk/config.json`

```json
"phoenix": {
  "command": "npx",
  "args": ["-y", "@arizeai/phoenix-mcp", "--baseUrl", "https://app.phoenix.arize.com"]
}
```

Gemini can query its own traces at runtime via the Phoenix MCP server. The agent introspects its own operational history to inform current decisions.

### 3. LLM-as-a-Judge Evaluations (Quality of Evals)

**File:** `agent/evals.py`

Gemini-2.0-flash evaluates every SENTINEL trace on three dimensions:

| Dimension | Description | Score |
|---|---|---|
| `patch_minimality` | Was the schema change as surgical as possible? | 0.0 – 1.0 |
| `violation_accuracy` | Were all violations correctly identified? No false positives? | 0.0 – 1.0 |
| `quarantine_correctness` | Were the right and only the right documents quarantined? | 0.0 – 1.0 |

Scores are written back to Phoenix via `POST /v1/span_annotations` — visible in the Phoenix dashboard.

### 4. Self-Improvement Loop (Bonus Points — WIN Condition)

Low-scoring traces (`overall < 0.75`) generate `improvement_hint` recommendations.

```python
result = run_self_improvement_loop(last_n_traces=10)
# Returns:
# {
#   "avg_overall_score": 0.91,
#   "improvement_recommendations": [
#     "When amount field is missing, check if it was renamed before declaring MISSING_REQUIRED_FIELD"
#   ]
# }
```

These hints inform future SENTINEL runs. The agent’s effective accuracy improves measurably as incident volume grows.

---

## Setup

```bash
pip install arize-phoenix-otel openinference-instrumentation-google-adk

# Get free API key at https://app.phoenix.arize.com
export ARIZE_PHOENIX_API_KEY=your_api_key

# Traces are automatically sent on every SENTINEL run
python -m agent.main orders

# Run evals manually
python -c "from agent.evals import run_self_improvement_loop; print(run_self_improvement_loop())"
```

---

*SENTINEL · Arize Track · Google Cloud Rapid Agent Hackathon 2026*
