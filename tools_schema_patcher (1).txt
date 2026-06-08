"""
Tool: patch_collection_schema
------------------------------
Surgically relaxes a MongoDB collection's $jsonSchema validator to sustain
live traffic during a schema drift incident. Never removes the entire
validator — only makes the minimum change needed (remove a field from
'required', or add an unknown field to 'properties').
"""
import copy
from pymongo import MongoClient
from agent.config import MONGODB_CONNECTION_STRING, MONGODB_DATABASE
from agent.tools.schema_inspector import inspect_collection_schema


def patch_collection_schema(
    collection_name: str,
    fields_to_make_optional: list = None,
    fields_to_add: dict = None,
    patch_reason: str = "Emergency schema relaxation by SENTINEL agent",
) -> dict:
    """
    Patches the MongoDB collection's JSON schema validator in-place.

    Args:
        collection_name:        Target MongoDB collection.
        fields_to_make_optional: List of field names to remove from 'required'.
        fields_to_add:          Dict of {field_name: bson_type_string} for
                                new fields to allow through the validator.
        patch_reason:           Human-readable reason stored in the patch log.

    Returns:
        dict with keys:
          - success (bool)
          - patch_applied (dict): what was changed
          - previous_schema_snapshot (dict): original schema before patch
          - validation_level (str): always "moderate" on success
          - error (str): only present on failure
    """
    client = MongoClient(MONGODB_CONNECTION_STRING)
    db = client[MONGODB_DATABASE]

    schema_info = inspect_collection_schema(collection_name)
    current_schema = copy.deepcopy(schema_info.get("schema", {}))
    previous_snapshot = copy.deepcopy(current_schema)

    patch_log = {"made_optional": [], "fields_added": []}

    # ── 1. Remove fields from 'required' ──────────────────────────────────────
    if fields_to_make_optional:
        required = current_schema.get("required", [])
        for field in fields_to_make_optional:
            if field in required:
                required.remove(field)
                patch_log["made_optional"].append(field)
        current_schema["required"] = required

    # ── 2. Add new field definitions to 'properties' ──────────────────────────
    if fields_to_add:
        properties = current_schema.setdefault("properties", {})
        for field_name, bson_type in fields_to_add.items():
            properties[field_name] = {"bsonType": bson_type}
            patch_log["fields_added"].append(field_name)

    # ── 3. Apply the patched schema via collMod ────────────────────────────────
    try:
        db.command({
            "collMod": collection_name,
            "validator": {"$jsonSchema": current_schema},
            "validationLevel": "moderate",   # NEVER "off"
            "validationAction": "warn",      # Log bad docs; don't reject traffic
        })
        client.close()
        return {
            "success": True,
            "patch_applied": patch_log,
            "previous_schema_snapshot": previous_snapshot,
            "patch_reason": patch_reason,
            "validation_level": "moderate",
        }
    except Exception as exc:
        client.close()
        return {
            "success": False,
            "error": str(exc),
            "patch_applied": {},
            "previous_schema_snapshot": previous_snapshot,
        }
