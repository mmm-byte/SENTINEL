from agent.jsonrpc.client import JSONRPCClient


class ArizeAdapter:
    def __init__(self, endpoint: str, **client_kwargs):
        self.client = JSONRPCClient(endpoint, **client_kwargs)

    def ingest_trace_and_evaluate(self, trace: dict):
        params = {"action": "ingest_and_score", "payload": {"trace": trace}}
        return self.client.call_method("mcp.exec", params)

    def get_compliance_report(self, run_id: str):
        params = {"action": "get_report", "payload": {"run_id": run_id}}
        return self.client.call_method("mcp.exec", params)
