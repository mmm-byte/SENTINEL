"""
SENTINEL Full End-to-End Demo Runner
=====================================
Runs the complete SENTINEL pipeline against the 'orders' collection.

One command to rule them all:
    python -m demo.run_demo

Prerequisites:
    1. cp .env.example .env  && fill in your values
    2. python -m demo.setup_demo_collection
    3. python -m demo.inject_schema_drift
    4. python -m demo.run_demo  ← YOU ARE HERE
"""

import asyncio
from rich.console import Console
from rich.panel import Panel
from rich.rule import Rule

from agent.main import run_sentinel
from agent.config import MONGODB_DATABASE

console = Console()

DEMO_ALERT = f"""
SYSTEM ALERT — Schema Violation Detected
==========================================
Collection  : {MONGODB_DATABASE}.orders
Alert Type  : schema_violation
Trigger     : Application deployment v2.4.1 pushed malformed payloads
              into the 'orders' collection. Two documents bypassed the
              validator via a legacy write path.

Known violations:
  • order_id field received as integer (expected string)
  • 'amount' field missing entirely on one document
  • amount field received as string "free" (expected double)

Priority    : CRITICAL — live order processing at risk
Instructions: Run the full SENTINEL pipeline.
              INSPECT schema → VALIDATE payload → PATCH safely →
              QUARANTINE corrupt docs → REPORT incident.
              Do NOT drop the validator. Sustain live traffic.
"""


async def main():
    console.print()
    console.print(Panel.fit(
        "[bold red]SENTINEL[/bold red] — Schema Continuity Agent\n"
        "[dim]Google Cloud Rapid Agent Hackathon 2026 · MongoDB Track[/dim]",
        border_style="bold red",
    ))
    console.print()
    console.print(Rule("[yellow]Incoming System Alert[/yellow]"))
    console.print(Panel(DEMO_ALERT.strip(), border_style="yellow"))
    console.print()
    console.print(Rule("[cyan]SENTINEL Agent Activating…[/cyan]"))
    console.print()

    response = await run_sentinel(DEMO_ALERT)

    console.print()
    console.print(Rule("[green]SENTINEL Pipeline Complete[/green]"))
    console.print()
    console.print(Panel(
        str(response),
        title="[bold green]Incident Report[/bold green]",
        border_style="green",
    ))
    console.print()


if __name__ == "__main__":
    asyncio.run(main())
