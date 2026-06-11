"""
SENTINEL — MongoDB Schema Continuity Agent
==========================================
Google Cloud Rapid Agent Hackathon 2026

Partner Tracks:
  Track 1 — MongoDB   : MCP Server + $jsonSchema pipeline + quarantine
  Track 2 — Arize     : OpenInference tracing + Phoenix MCP + LLM evals + self-improvement
  Track 3 — Dynatrace : Dual OTel export + SENTINEL custom span attributes
  Track 4 — Fivetran  : MCP server + REST API + connector auto-discovery
  Track 5 — GitLab    : Duo Agent Platform custom agent + MCP server + pipeline status
  Track 6 — Elastic   : ES|QL tools + hybrid search + ELSER memory layer + MCP

Entry point: python -m agent.main
Web UI:      adk web
"""

import asyncio
import json
import os

from google.adk.agents import LlmAgent
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.adk.tools.mcp_tool.mcp_toolset import MCPToolset, StdioServerParameters
from google.genai import types

from agent.config import (
    GEMINI_MODEL,
    GOOGLE_API_KEY,
    GOOGLE_CLOUD_LOCATION,
    GOOGLE_CLOUD_PROJECT,
    MONGODB_CONNECTION_STRING,
)
from agent.tools import (
    generate_incident_report,
    inspect_collection_schema,
    patch_collection_schema,
    quarantine_corrupt_documents,
    validate_payload_against_schema,
)
from agent.tools.elastic_memory import (
    search_incident_history,
    esql_query_incidents,
    get_incident_stats,
)
from orchestrator.fivetran_agent import (
    list_fivetran_connectors,
    get_connector_for_collection,
    trigger_fivetran_resync,
)
from orchestrator.gitlab_agent import (
    open_rollback_merge_request,
    get_gitlab_pipeline_status,
)

# ── Observability: Arize Phoenix + Dynatrace ──────────────────────────────────
from agent.observability import setup_observability
setup_observability()

if GOOGLE_API_KEY:
    os.environ["GOOGLE_API_KEY"] = GOOGLE_API_KEY

# ── SENTINEL system instruction ────────────────────────────────────────────────
SENTINEL_INSTRUCTION = """
You are SENTINEL, an autonomous MongoDB database continuity agent.
Powered by Google ADK + Gemini 2.0 Flash.
Integrated with: MongoDB · Arize Phoenix · Dynatrace · Elastic · Fivetran · GitLab Duo.

When you receive a schema violation alert, execute this EXACT pipeline:

════════════════════════════════════════════════════════════════
STEP 0 — MEMORY CHECK (Elastic)
  Call search_incident_history(collection_name) to check if SENTINEL has
  seen similar violations before. If a past CONTAINED fix exists, adopt that
  patch strategy directly. Also call esql_query_incidents with:
  'FROM sentinel_incidents | WHERE collection_name == "<name>" | SORT timestamp DESC | LIMIT 3'

STEP 1 — INSPECT (MongoDB)
  Call inspect_collection_schema to read the live $jsonSchema validator.

STEP 2 — VALIDATE (MongoDB)
  Call validate_payload_against_schema. List EVERY violation precisely.

STEP 3 — PATCH (MongoDB)
  Call patch_collection_schema. ONLY relax fields with active violations.
  ALWAYS use validationLevel="moderate". NEVER use "off".

STEP 4 — QUARANTINE (MongoDB)
  Call quarantine_corrupt_documents. Move corrupt docs to shadow collection.
  NEVER delete. Include a clear remediation_hint.

STEP 5 — REPORT
  Call generate_incident_report. Set final_status:
    "CONTAINED"  — all steps succeeded
    "ESCALATE"   — any step failed or violations were critical
  The report automatically:
    • Runs LLM-as-a-Judge eval and writes score to Arize Phoenix (Track 2)
    • Emits SENTINEL span attributes to Dynatrace (Track 3)
    • Indexes report to Elastic memory (Track 6)
    • Opens GitLab rollback MR if ESCALATE (Track 5)

STEP 6 — DOWNSTREAM SYNC (Fivetran)
  Call get_connector_for_collection(collection_name) to find the connector.
  Then call trigger_fivetran_resync(connector_id) to re-align the warehouse.

STEP 7 — PIPELINE CHECK (GitLab)
  Call get_gitlab_pipeline_status() to verify CI is passing on main.
  Report the pipeline status in your final summary.

STEP 8 — STATS (Elastic)
  Call get_incident_stats() to show cumulative SENTINEL performance:
  total incidents, resolution rate, escalation rate.
════════════════════════════════════════════════════════════════

CRITICAL RULES:
  - Never skip steps 1–5. All must run every time.
  - Never use validationLevel="off".
  - Never delete documents — quarantine only.
  - If any step fails, continue to REPORT with ESCALATE status.
  - Present the final report with: INCIDENT ID, STATUS, executive summary,
    numbered violations, next-action checklist, and Arize eval score.
"""


def build_sentinel_agent() -> LlmAgent:
    # ── Track 1: MongoDB MCP ──────────────────────────────────────────────────────
    mongodb_mcp = MCPToolset(
        connection_params=StdioServerParameters(
            command="npx",
            args=["-y", "@mongodb-js/mongodb-mcp-server",
                  "--connectionString", MONGODB_CONNECTION_STRING],
        )
    )

    # ── Track 2: Arize Phoenix MCP (self-introspection) ───────────────────────
    arize_mcp_tools = []
    if os.environ.get("ARIZE_PHOENIX_API_KEY"):
        try:
            arize_mcp_tools = [MCPToolset(
                connection_params=StdioServerParameters(
                    command="npx",
                    args=["-y", "@arizeai/phoenix-mcp",
                          "--baseUrl", "https://app.phoenix.arize.com"],
                    env={"PHOENIX_API_KEY": os.environ["ARIZE_PHOENIX_API_KEY"]},
                )
            )]
        except Exception:
            pass

    # ── Track 4: Fivetran MCP ──────────────────────────────────────────────────
    fivetran_mcp_tools = []
    if os.environ.get("FIVETRAN_API_KEY"):
        try:
            fivetran_mcp_tools = [MCPToolset(
                connection_params=StdioServerParameters(
                    command="npx",
                    args=["-y", "fivetran-mcp"],
                    env={
                        "FIVETRAN_API_KEY": os.environ["FIVETRAN_API_KEY"],
                        "FIVETRAN_API_SECRET": os.environ.get("FIVETRAN_API_SECRET", ""),
                    },
                )
            )]
        except Exception:
            pass

    # ── Track 5: GitLab MCP ────────────────────────────────────────────────────
    gitlab_mcp_tools = []
    if os.environ.get("GITLAB_TOKEN"):
        try:
            gitlab_mcp_tools = [MCPToolset(
                connection_params=StdioServerParameters(
                    command="npx",
                    args=["-y", "@gitlab-org/gitlab-mcp-server"],
                    env={
                        "GITLAB_TOKEN": os.environ["GITLAB_TOKEN"],
                        "GITLAB_API_URL": os.environ.get("GITLAB_API_URL",
                                                         "https://gitlab.com/api/v4"),
                    },
                )
            )]
        except Exception:
            pass

    agent = LlmAgent(
        model=GEMINI_MODEL,
        name="sentinel_mongodb_agent",
        description=(
            "Autonomous MongoDB schema continuity agent. "
            "Detects, patches, quarantines, and reports schema violations in real time. "
            "Tracks: MongoDB · Arize · Dynatrace · Elastic · Fivetran · GitLab"
        ),
        instruction=SENTINEL_INSTRUCTION,
        tools=[
            mongodb_mcp,
            *arize_mcp_tools,
            *fivetran_mcp_tools,
            *gitlab_mcp_tools,
            # Core 5-step pipeline
            inspect_collection_schema,
            validate_payload_against_schema,
            patch_collection_schema,
            quarantine_corrupt_documents,
            generate_incident_report,
            # Track 4: Fivetran (REST + auto-discovery)
            list_fivetran_connectors,
            get_connector_for_collection,
            trigger_fivetran_resync,
            # Track 5: GitLab
            open_rollback_merge_request,
            get_gitlab_pipeline_status,
            # Track 6: Elastic (ES|QL tools + memory)
            search_incident_history,
            esql_query_incidents,
            get_incident_stats,
        ],
    )
    return agent


root_agent = build_sentinel_agent()


async def run_sentinel(collection_name: str, corrupt_payload: dict) -> None:
    session_service = InMemorySessionService()
    runner = Runner(
        agent=root_agent,
        app_name="sentinel",
        session_service=session_service,
    )
    session = await session_service.create_session(
        app_name="sentinel", user_id="operator",
    )
    alert_message = (
        f"ALERT: Schema violation detected.\n"
        f"Collection: {collection_name}\n"
        f"Corrupt payload:\n{json.dumps(corrupt_payload, indent=2)}\n\n"
        f"Run the full SENTINEL pipeline now."
    )

    print(f"\n{'='*60}")
    print("  SENTINEL — MongoDB Schema Continuity Agent")
    print("  Tracks: MongoDB · Arize · Dynatrace · Elastic · Fivetran · GitLab")
    print(f"{'='*60}\n")

    async for event in runner.run_async(
        user_id="operator",
        session_id=session.id,
        new_message=types.Content(
            role="user",
            parts=[types.Part(text=alert_message)],
        ),
    ):
        if event.is_final_response():
            print(event.content.parts[0].text)


if __name__ == "__main__":
    test_payload = {
        "order_id": 12345,
        "customer_name": "Alice",
        "status": "pending",
    }
    asyncio.run(run_sentinel("orders", test_payload))
