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

    if action == "search_logs":
        return {
            "jsonrpc": "2.0",
            "id": req.id,
            "result": {
                "error_string": "BSONType mismatch: expected objectId",
                "file_path": "src/payments/processor.py",
                "sample_log_entries": [
                    "2026-06-09T10:00:02Z ERROR BSONType mismatch: expected objectId at src/payments/processor.py:243",
                ],
            },
        }

    return {"jsonrpc": "2.0", "id": req.id, "error": {"code": -32601, "message": "unknown action"}}


def run():
    uvicorn.run(app, host="127.0.0.1", port=9002)


if __name__ == "__main__":
    run()
