from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
import uvicorn
from datetime import datetime
import os

app = FastAPI(title="SRE Control Cockpit")


class StageStatus(BaseModel):
    name: str
    status: str  # idle, running, success, error
    duration_ms: int = 0
    error: str = None


class ExecutionStatus(BaseModel):
    timestamp: str
    mttd_ms: float
    mttr_ms: float
    system_health: str  # critical, warning, healthy
    stages: list[StageStatus]
    timeline_events: list[str]


# Serve static UI
@app.get("/")
async def serve_ui():
    ui_path = os.path.join(os.path.dirname(__file__), "..", "ui", "index.html")
    return FileResponse(ui_path)


# API endpoint for live status
@app.get("/api/status")
async def get_status() -> ExecutionStatus:
    """Return current execution status for the cockpit UI."""
    return ExecutionStatus(
        timestamp=datetime.utcnow().isoformat(),
        mttd_ms=120.0,
        mttr_ms=11420.0,
        system_health="critical",
        stages=[
            StageStatus(name="Dynatrace", status="success", duration_ms=2120),
            StageStatus(name="Elastic", status="success", duration_ms=2770),
            StageStatus(name="GitLab", status="success", duration_ms=5186),
            StageStatus(name="MongoDB", status="idle"),
            StageStatus(name="Fivetran", status="idle"),
            StageStatus(name="Arize", status="idle"),
        ],
        timeline_events=[
            "✓ [10:00:00.000] Stage 1: Dynatrace topology query completed",
            "✓ [10:00:02.120] Stage 2: Elastic logs parsed",
            "✓ [10:00:04.890] Stage 3: GitLab blame completed",
            "✓ [10:00:06.234] Hotfix branch created",
            "✓ [10:00:11.420] Merge Request opened",
            "⟳ [10:00:12.100] Awaiting Stage 4...",
        ],
    )


def run(host: str = "127.0.0.1", port: int = 8080):
    """Start the UI server."""
    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    run()
