import uuid
import httpx
from typing import Any, Dict, Optional


class JSONRPCError(Exception):
    pass


class JSONRPCClient:
    def __init__(self, endpoint: str, timeout: int = 10):
        self.endpoint = endpoint
        self.timeout = timeout

    def call_method(self, method: str, params: Dict[str, Any], id: Optional[str] = None) -> Any:
        if id is None:
            id = str(uuid.uuid4())

        payload = {
            "jsonrpc": "2.0",
            "id": id,
            "method": method,
            "params": params,
        }

        try:
            resp = httpx.post(self.endpoint, json=payload, timeout=self.timeout)
        except Exception as e:
            raise JSONRPCError(f"transport error: {e}")

        if resp.status_code != 200:
            raise JSONRPCError(f"bad status: {resp.status_code} - {resp.text}")

        body = resp.json()
        if "error" in body:
            raise JSONRPCError(body["error"])
        if "result" not in body:
            raise JSONRPCError(f"invalid response: {body}")

        return body["result"]
