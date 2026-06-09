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

    if action == "adjust_connector":
        return {"jsonrpc": "2.0", "id": req.id, "result": {"status": "mapping_updated"}}

    if action == "trigger_resync":
        return {"jsonrpc": "2.0", "id": req.id, "result": {"status": "resync_started"}}

    return {"jsonrpc": "2.0", "id": req.id, "error": {"code": -32601, "message": "unknown action"}}


def run():
    uvicorn.run(app, host="127.0.0.1", port=9006)


if __name__ == "__main__":
    run()
