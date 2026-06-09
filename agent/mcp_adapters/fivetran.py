from agent.jsonrpc.client import JSONRPCClient


class FivetranAdapter:
    def __init__(self, endpoint: str):
        self.client = JSONRPCClient(endpoint)

    def adjust_connector(self, connector_id: str, mapping_changes: dict):
        params = {
            "action": "adjust_connector",
            "payload": {"connector_id": connector_id, "mapping_changes": mapping_changes},
        }
        return self.client.call_method("mcp.exec", params)

    def trigger_resync(self, connector_id: str):
        params = {"action": "trigger_resync", "payload": {"connector_id": connector_id}}
        return self.client.call_method("mcp.exec", params)
