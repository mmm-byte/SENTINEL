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

    if action == "query_blame":
        # Return a deterministic mock blame result
        return {
            "jsonrpc": "2.0",
            "id": req.id,
            "result": {
                "recent_commits": [
                    {
                        "sha": "fa83b2cc1deadbeef",
                        "author": "alice@example.com",
                        "message": "refactor: update BSON validation schema",
                        "timestamp": "2026-06-08T15:30:00Z",
                    }
                ],
            },
        }

    if action == "create_branch":
        return {
            "jsonrpc": "2.0",
            "id": req.id,
            "result": {
                "branch_name": "hotfix/auto/2026-06-09-agent-0a1b2c",
                "commit_sha": "fa83b2cc1deadbeef",
            },
        }

    if action == "create_merge_request":
        return {
            "jsonrpc": "2.0",
            "id": req.id,
            "result": {
                "merge_request_url": "https://gitlab.com/org/repo/-/merge_requests/42",
                "merge_request_id": 42,
            },
        }

    return {"jsonrpc": "2.0", "id": req.id, "error": {"code": -32601, "message": "unknown action"}}


def run():
    uvicorn.run(app, host="127.0.0.1", port=9004)


if __name__ == "__main__":
    run()
