from agent.jsonrpc.client import JSONRPCClient


class GitLabAdapter:
    def __init__(self, endpoint: str, **client_kwargs):
        self.client = JSONRPCClient(endpoint, **client_kwargs)

    def query_blame(self, file_path: str):
        params = {
            "action": "query_blame",
            "payload": {"file_path": file_path},
        }
        return self.client.call_method("mcp.exec", params)

    def create_branch(self, branch_name: str, from_sha: str = None):
        params = {
            "action": "create_branch",
            "payload": {"branch_name": branch_name, "from_sha": from_sha},
        }
        return self.client.call_method("mcp.exec", params)

    def create_merge_request(self, branch_name: str, title: str, description: str = None):
        params = {
            "action": "create_merge_request",
            "payload": {
                "branch_name": branch_name,
                "title": title,
                "description": description,
            },
        }
        return self.client.call_method("mcp.exec", params)
