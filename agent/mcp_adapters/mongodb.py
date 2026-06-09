from agent.jsonrpc.client import JSONRPCClient


class MongoDBAdapter:
    def __init__(self, endpoint: str, **client_kwargs):
        self.client = JSONRPCClient(endpoint, **client_kwargs)

    def modify_collection_validator(self, db: str, collection: str, modification: dict):
        params = {
            "action": "collMod",
            "payload": {"db": db, "collection": collection, "modification": modification},
        }
        return self.client.call_method("mcp.exec", params)

    def quarantine_documents(self, db: str, collection: str, query: dict, target_collection: str):
        params = {
            "action": "quarantine",
            "payload": {"db": db, "collection": collection, "query": query, "target_collection": target_collection},
        }
        return self.client.call_method("mcp.exec", params)
