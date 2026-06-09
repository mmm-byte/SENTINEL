"""
Tool: inspect_collection_schema
--------------------------------
Reads the current $jsonSchema validator attached to a MongoDB collection.
Returns the full schema, required fields list, and property definitions.
If no validator exists, returns safe empty defaults.
"""
from pymongo import MongoClient
from agent.config import MONGODB_CONNECTION_STRING, MONGODB_DATABASE


def inspect_collection_schema(connection_string: str = None, database_name: str = None, collection_name: str = None) -> dict:
    """
    Inspects the current JSON Schema validator of a MongoDB collection.

    Args:
        collection_name: The name of the MongoDB collection to inspect.

    Returns:
        dict with keys:
          - collection_exists (bool)
          - has_validator (bool)
          - schema (dict): the full $jsonSchema object
          - required_fields (list[str]): fields marked as required
          - properties (dict): field definitions keyed by field name
    """
    conn = connection_string or MONGODB_CONNECTION_STRING
    db_name = database_name or MONGODB_DATABASE

    client = MongoClient(conn)
    db = client[db_name]

    coll_info = list(db.list_collections(filter={"name": collection_name}))

    if not coll_info:
        return {
            "collection_exists": False,
            "has_validator": False,
            "schema": {},
            "required_fields": [],
            "properties": {},
        }

    options = coll_info[0].get("options", {})
    validator = options.get("validator", {})
    json_schema = validator.get("$jsonSchema", {})
    required_fields = json_schema.get("required", [])
    properties = json_schema.get("properties", {})

    client.close()

    return {
        "collection_exists": True,
        "has_validator": bool(validator),
        "schema": json_schema,
        "required_fields": required_fields,
        "properties": properties,
    }
