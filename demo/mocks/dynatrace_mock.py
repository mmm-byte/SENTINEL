from fastapi import FastAPI, Request
from pydantic import BaseModel
import uvicorn

app = FastAPI()


class RPCRequest(BaseModel):
    jsonrpc: str
    id: str
    method: str
    params: dict


@app.post("/mcp")
async def mcp_endpoint(req: RPCRequest):
    params = req.params or {}
    action = params.get("action")

    if action == "query_topology":
        # Return a deterministic mock
        return {
            "jsonrpc": "2.0",
            "id": req.id,
            "result": {
                "service_id": "svc-payments",
                "pod_id": "k8s-pod-x92-node4",
                "container_signature": "sha256:deadbeef",
                "time_window": "2026-06-09T10:00:00Z/2026-06-09T10:02:00Z",
            },
        }

    return {"jsonrpc": "2.0", "id": req.id, "error": {"code": -32601, "message": "unknown action"}}


def run():
    uvicorn.run(app, host="127.0.0.1", port=9001)


if __name__ == "__main__":
    run()
