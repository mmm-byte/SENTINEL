"""Re-export the signed JSON-RPC client under the core namespace."""
from agent.jsonrpc.client import (  # noqa: F401
    JSONRPCClient,
    JSONRPCError,
)

__all__ = ["JSONRPCClient", "JSONRPCError"]
