from fastapi import FastAPI
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

    if action == "collMod":
        payload = params.get("payload", {})
        return {
            "jsonrpc": "2.0",
            "id": req.id,
            "result": {
                "status": "ok",
                "applied_modification": payload.get("modification"),
            },
        }

    if action == "quarantine":
        payload = params.get("payload", {})
        return {
            "jsonrpc": "2.0",
            "id": req.id,
            "result": {
                "quarantined_count": 3,
                "target_collection": payload.get("target_collection"),
            },
        }

    return {"jsonrpc": "2.0", "id": req.id, "error": {"code": -32601, "message": "unknown action"}}


def run():
    uvicorn.run(app, host="127.0.0.1", port=9005)


if __name__ == "__main__":
    run()
