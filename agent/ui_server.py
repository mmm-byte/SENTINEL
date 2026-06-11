"""SRE Control Cockpit FastAPI server.

This module exposes:
  GET  /            -> the SRE Control Cockpit HTML
  GET  /api/status  -> live status JSON (drives the UI)
  POST /api/run     -> trigger a healing run
  POST /api/approve -> approve the pending Stage 4 schema change
  POST /api/reject  -> reject the pending Stage 4 schema change

It uses a MockOrchestrator by default so the UI works end-to-end with
no cloud credentials. The real Orchestrator can be wired in by replacing
the ``_driver`` factory.
"""
from __future__ import annotations

import os
from typing import Any, Dict

from fastapi import FastAPI
from fastapi.responses import FileResponse, JSONResponse
import uvicorn

from agent.mock_orchestrator import MockOrchestrator

app = FastAPI(title="SENTINEL · SRE Control Cockpit")
_driver = MockOrchestrator()


# ── UI serving ────────────────────────────────────────────────────────────────
_UI_DIR = os.path.join(os.path.dirname(__file__), "..", "ui", "cockpit")
os.makedirs(_UI_DIR, exist_ok=True)


@app.get("/")
async def serve_index() -> FileResponse:
    return FileResponse(os.path.join(_UI_DIR, "index.html"))


# ── API ───────────────────────────────────────────────────────────────────────
@app.get("/api/status")
async def get_status() -> JSONResponse:
    return JSONResponse(_driver.status())


@app.post("/api/run")
async def post_run() -> Dict[str, Any]:
    run_id = _driver.trigger()
    return {"ok": True, "run_id": run_id}


@app.post("/api/approve")
async def post_approve() -> Dict[str, Any]:
    _driver.approve()
    return {"ok": True}


@app.post("/api/reject")
async def post_reject() -> Dict[str, Any]:
    _driver.reject()
    return {"ok": True}


def run(host: str = "127.0.0.1", port: int = 8080) -> None:
    """Start the cockpit UI server (dev mode)."""
    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    run()

