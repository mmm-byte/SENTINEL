"""Re-export the existing MCP adapter implementations under the core namespace.

Dynatrace and Elastic are not yet first-class adapter classes — the
orchestrator speaks to them through a generic JSONRPCClient. We still expose
lightweight adapter classes here so per-track repos can use a uniform
``Adapter(endpoint, **client_kwargs)`` API.
"""
from agent.jsonrpc.client import JSONRPCClient
from agent.mcp_adapters.arize import ArizeAdapter  # noqa: F401
from agent.mcp_adapters.fivetran import FivetranAdapter  # noqa: F401
from agent.mcp_adapters.gitlab import GitLabAdapter  # noqa: F401
from agent.mcp_adapters.mongodb import MongoDBAdapter  # noqa: F401


class DynatraceAdapter:
    """Thin wrapper that exposes the same ``mcp.exec`` surface as the others."""

    def __init__(self, endpoint: str, **client_kwargs):
        self.client = JSONRPCClient(endpoint, **client_kwargs)

    def query_topology(self, alert_id: str):
        return self.client.call_method(
            "mcp.exec",
            {"action": "query_topology", "payload": {"alert_id": alert_id}},
        )


class ElasticAdapter:
    """Thin wrapper for the log-search stage."""

    def __init__(self, endpoint: str, **client_kwargs):
        self.client = JSONRPCClient(endpoint, **client_kwargs)

    def search_logs(self, query: dict):
        return self.client.call_method(
            "mcp.exec",
            {"action": "search_logs", "payload": query},
        )


__all__ = [
    "ArizeAdapter",
    "ElasticAdapter",
    "FivetranAdapter",
    "GitLabAdapter",
    "MongoDBAdapter",
    "DynatraceAdapter",
]
