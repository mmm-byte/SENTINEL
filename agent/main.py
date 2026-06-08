"""
SENTINEL — MongoDB Schema Continuity Agent
==========================================
Google Cloud Rapid Agent Hackathon 2026
Partner Track: MongoDB

Entry point for the SENTINEL agent. Combines:
  - MongoDB MCP Server (official partner integration)
  - Custom 5-step tool pipeline (SENTINEL-specific logic)

Run locally:   python -m agent.main
Web UI:        adk web
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

# ── Gemini auth: prefer Vertex AI, fall back to AI Studio key ─────────────────
if GOOGLE_API_KEY:
    os.environ["GOOGLE_API_KEY"] = GOOGLE_API_KEY

# ── SENTINEL system instruction ───────────────────────────────────────────────
SENTINEL_INSTRUCTION = """
You are SENTINEL, an autonomous MongoDB database continuity agent built on
Google ADK and powered by Gemini. Your mission is to detect, contain, and
report schema violations in real-time without interrupting application traffic.

When you receive a schema violation alert containing a collection name and a
corrupt payload, you MUST execute this exact 5-step pipeline in sequence:

STEP 1 — INSPECT
  Call `inspect_collection_schema` to read the current $jsonSchema validator
  of the affected collection. Understand which fields are required and what
  types are enforced.

STEP 2 — VALIDATE
  Call `validate_payload_against_schema` with the collection name and the
  incoming payload. Enumerate all field-level violations precisely:
  MISSING_REQUIRED_FIELD or TYPE_MISMATCH.

STEP 3 — PATCH
  Call `patch_collection_schema` to surgically relax only the rules that are
  blocking live traffic. Use fields_to_make_optional for missing required fields
  and fields_to_add for unknown new fields. Never drop the entire validator.
  Always use validationLevel="moderate" — never "off".

STEP 4 — QUARANTINE
  Call `quarantine_corrupt_documents` to move the identified corrupt documents
  to the quarantine shadow collection. Include a clear remediation_hint for the
  human reviewer. Do NOT delete documents — only move them.

STEP 5 — REPORT
  Call `generate_incident_report` to synthesize the full pipeline run into a
  structured incident report. Set resolution_status to "CONTAINED" if all steps
  succeeded, or "ESCALATE" if any step failed.

After all 5 steps, present the incident report clearly:
  - Lead with the INCIDENT ID and STATUS
  - Show the executive summary
  - List violations in a numbered format
  - List next actions as a checklist

CRITICAL RULES:
  - Never skip a step. All 5 must run every time.
  - Never set validationLevel to "off" — always use "moderate" during patches.
  - Never permanently delete documents — quarantine only.
  - If a step fails, still continue to the report step with ESCALATE status.
  - You have access to the MongoDB MCP tools for raw database operations.
    Use them for ad-hoc queries or diagnostics outside the 5-step pipeline.
"""


def build_sentinel_agent() -> LlmAgent:
    """
    Constructs the SENTINEL LlmAgent with:
      - MongoDB MCP Server toolset (official partner MCP integration)
      - Custom 5-step SENTINEL pipeline tools
    """
    # ── MongoDB MCP Server (official partner integration) ──────────────────────
    # This gives the agent native MongoDB capabilities: find, aggregate,
    # listCollections, createIndex, runCommand, etc.
    mongodb_mcp_toolset = MCPToolset(
        connection_params=StdioServerParameters(
            command="npx",
            args=[
                "-y",
                "@mongodb-js/mongodb-mcp-server",
                "--connectionString",
                MONGODB_CONNECTION_STRING,
            ],
        )
    )

    # ── SENTINEL custom pipeline tools ────────────────────────────────────────
    custom_tools = [
        inspect_collection_schema,
        validate_payload_against_schema,
        patch_collection_schema,
        quarantine_corrupt_documents,
        generate_incident_report,
    ]

    agent = LlmAgent(
        model=GEMINI_MODEL,
        name="sentinel_mongodb_agent",
        description=(
            "Autonomous MongoDB schema continuity agent. "
            "Detects, patches, quarantines, and reports schema violations "
            "in real time without interrupting application traffic."
        ),
        instruction=SENTINEL_INSTRUCTION,
        tools=[mongodb_mcp_toolset, *custom_tools],
    )
    return agent


# ── Module-level agent instance (used by `adk web` and `adk run`) ─────────────
root_agent = build_sentinel_agent()


# ── Standalone runner for direct CLI execution ────────────────────────────────
async def run_sentinel(collection_name: str, corrupt_payload: dict) -> None:
    """
    Runs the SENTINEL pipeline once against a given collection + payload.
    Use this for testing or scripted invocations.
    """
    session_service = InMemorySessionService()
    runner = Runner(
        agent=root_agent,
        app_name="sentinel",
        session_service=session_service,
    )

    session = await session_service.create_session(
        app_name="sentinel",
        user_id="operator",
    )

    alert_message = (
        f"ALERT: Schema violation detected.\n"
        f"Collection: {collection_name}\n"
        f"Corrupt payload received:\n{json.dumps(corrupt_payload, indent=2)}\n\n"
        f"Run the full 5-step SENTINEL pipeline now."
    )

    print(f"\n{'='*60}")
    print("  SENTINEL — MongoDB Schema Continuity Agent")
    print(f"{'='*60}")
    print(f"  Target collection : {collection_name}")
    print(f"  Payload fields    : {list(corrupt_payload.keys())}")
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
    # Quick smoke-test: simulate a corrupt payload hitting the 'orders' collection
    test_payload = {
        "order_id": 12345,        # TYPE_MISMATCH: should be string
        "customer_name": "Alice",
        # "amount" field is missing — MISSING_REQUIRED_FIELD
        "status": "pending",
    }
    asyncio.run(run_sentinel("orders", test_payload))
