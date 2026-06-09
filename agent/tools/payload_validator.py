"""
Tool: validate_payload_against_schema
--------------------------------------
Checks an incoming document payload against the collection's current
$jsonSchema validator. Returns field-level violations with severity rating.
"""
from agent.tools.schema_inspector import inspect_collection_schema


def validate_payload_against_schema(payload: dict = None, schema: dict = None, collection_name: str = None) -> dict:
    """
    Validates a payload dict against the collection's JSON schema validator.

    Args:
        collection_name: MongoDB collection name.
        payload: The incoming document to validate.

    Returns:
        dict with keys:
          - is_valid (bool)
          - violations (list): each item has {field, issue, expected, received}
          - severity ("OK" | "WARNING" | "CRITICAL")
          - violation_count (int)
    """
    if schema is None:
        schema_info = inspect_collection_schema(collection_name=collection_name)
        required_fields = schema_info.get("required_fields", [])
        properties = schema_info.get("properties", {})
    else:
        required_fields = schema.get("required", [])
        properties = schema.get("properties", {})

    violations = []

    # ── Check 1: Required fields presence ─────────────────────────────────────
    for field in required_fields:
        if field not in payload:
            violations.append({
                "field": field,
                "violation_type": "MISSING_REQUIRED_FIELD",
                "expected": "field to be present",
                "received": "null / missing",
            })

    # ── Check 2: Field type conformance ───────────────────────────────────────
    bson_to_python = {
        "string": str,
        "int": int,
        "long": int,
        "double": float,
        "decimal": float,
        "bool": bool,
        "array": list,
        "object": dict,
    }

    for field, field_schema in properties.items():
        if field not in payload:
            continue
        expected_type = field_schema.get("bsonType") or field_schema.get("type")
        received_value = payload[field]
        py_type = bson_to_python.get(expected_type)

        if py_type and not isinstance(received_value, py_type):
            violations.append({
                "field": field,
                "violation_type": "TYPE_MISMATCH",
                "expected": expected_type,
                "received": type(received_value).__name__,
            })

    # ── Severity classification ────────────────────────────────────────────────
    if not violations:
        severity = "OK"
    elif any(v.get("violation_type") in ("MISSING_REQUIRED_FIELD", "TYPE_MISMATCH") for v in violations):
        severity = "CRITICAL"
    else:
        severity = "WARNING"

    return {
        "overall_severity": severity,
        "violations": violations,
        "violation_count": len(violations),
        "is_valid": len(violations) == 0,
    }
