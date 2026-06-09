from fastapi import FastAPI, Header, HTTPException, Request
from pydantic import BaseModel
from agent.jsonrpc.client import JSONRPCClient
import uvicorn

app = FastAPI(title="Agent Gateway")


class RPCRequest(BaseModel):
    jsonrpc: str
    id: str
    method: str
    params: dict


def validate_agent_auth(x_agent_id: str, authorization: str) -> bool:
    # Stubbed auth validation. Replace with mTLS/JWT verification.
    if not x_agent_id:
        return False
    if not authorization or not authorization.startswith("Bearer "):
        return False
    # In production: verify token, map agent_id -> service account, check IAM
    return True


@app.post("/proxy")
async def proxy_endpoint(req: RPCRequest, x_agent_id: str | None = Header(None), authorization: str | None = Header(None)):
    if not validate_agent_auth(x_agent_id, authorization):
        raise HTTPException(status_code=401, detail="unauthorized agent")

    # Rudimentary routing: expect params.endpoint set to target MCP URL
    params = req.params or {}
    target = params.get("endpoint")
    if not target:
        raise HTTPException(status_code=400, detail="missing target endpoint in params")

    client = JSONRPCClient(target)
    try:
        result = client.call_method(req.method, params.get("payload", {}), id=req.id)
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))

    return {"jsonrpc": "2.0", "id": req.id, "result": result}


def run(host: str = "127.0.0.1", port: int = 9003):
    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    run()
