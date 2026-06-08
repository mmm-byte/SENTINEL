"""
SENTINEL Unit Tests
===================
Smoke tests for all 5 pipeline tools using an in-memory mock MongoDB.
No Atlas connection required — uses mongomock for offline testing.

Install test deps:
    pip install pytest mongomock

Run:
    pytest tests/ -v
"""

import pytest
from unittest.mock import patch, MagicMock
from bson import ObjectId

# ── Fixtures ──────────────────────────────────────────────────────────────────

STRICT_SCHEMA = {
    "bsonType": "object",
    "required": ["order_id", "customer_name", "amount", "status", "created_at"],
    "properties": {
        "order_id":      {"bsonType": "string"},
        "customer_name": {"bsonType": "string"},
        "amount":        {"bsonType": "double"},
        "status":        {"bsonType": "string"},
        "created_at":    {"bsonType": "string"},
    },
}

VALID_PAYLOAD = {
    "order_id": "ORD-001",
    "customer_name": "Alice Johnson",
    "amount": 129.99,
    "status": "confirmed",
    "created_at": "2026-06-08T10:00:00Z",
}

CORRUPT_PAYLOAD_MISSING_FIELD = {
    "order_id": "ORD-BAD",
    "customer_name": "Dave Corrupt",
    # "amount" is missing
    "status": "pending",
    "created_at": "2026-06-08T12:35:00Z",
}

CORRUPT_PAYLOAD_TYPE_MISMATCH = {
    "order_id": 99999,                   # int, should be string
    "customer_name": "Eve Broken",
    "amount": "free",                    # string, should be double
    "status": "pending",
    "created_at": "2026-06-08T12:36:00Z",
}


# ── schema_inspector tests ────────────────────────────────────────────────────

class TestSchemaInspector:
    def test_inspect_collection_with_validator(self):
        """inspect_collection_schema should detect a $jsonSchema validator."""
        from agent.tools.schema_inspector import inspect_collection_schema

        mock_client = MagicMock()
        mock_db = mock_client["sentinel_demo"]
        mock_db.list_collection_names.return_value = ["orders"]
        mock_db.list_collections.return_value = iter([
            {
                "name": "orders",
                "options": {"validator": {"$jsonSchema": STRICT_SCHEMA}},
            }
        ])

        with patch("agent.tools.schema_inspector.MongoClient", return_value=mock_client):
            result = inspect_collection_schema(
                connection_string="mongodb://mock",
                database_name="sentinel_demo",
                collection_name="orders",
            )

        assert result["collection_exists"] is True
        assert result["has_validator"] is True
        assert result["schema"]["bsonType"] == "object"
        assert "amount" in result["required_fields"]

    def test_inspect_nonexistent_collection(self):
        """inspect_collection_schema should report missing collection gracefully."""
        from agent.tools.schema_inspector import inspect_collection_schema

        mock_client = MagicMock()
        mock_db = mock_client["sentinel_demo"]
        mock_db.list_collection_names.return_value = []

        with patch("agent.tools.schema_inspector.MongoClient", return_value=mock_client):
            result = inspect_collection_schema(
                connection_string="mongodb://mock",
                database_name="sentinel_demo",
                collection_name="nonexistent",
            )

        assert result["collection_exists"] is False
        assert result["has_validator"] is False


# ── payload_validator tests ───────────────────────────────────────────────────

class TestPayloadValidator:
    def test_valid_payload_passes(self):
        """validate_payload_against_schema should return OK for a correct document."""
        from agent.tools.payload_validator import validate_payload_against_schema

        result = validate_payload_against_schema(
            payload=VALID_PAYLOAD,
            schema=STRICT_SCHEMA,
        )
        assert result["overall_severity"] == "OK"
        assert result["violation_count"] == 0
        assert result["violations"] == []

    def test_missing_required_field_detected(self):
        """validate_payload_against_schema should catch MISSING_REQUIRED_FIELD."""
        from agent.tools.payload_validator import validate_payload_against_schema

        result = validate_payload_against_schema(
            payload=CORRUPT_PAYLOAD_MISSING_FIELD,
            schema=STRICT_SCHEMA,
        )
        types = [v["violation_type"] for v in result["violations"]]
        assert "MISSING_REQUIRED_FIELD" in types
        assert result["overall_severity"] in ("WARNING", "CRITICAL")

    def test_type_mismatch_detected(self):
        """validate_payload_against_schema should catch TYPE_MISMATCH violations."""
        from agent.tools.payload_validator import validate_payload_against_schema

        result = validate_payload_against_schema(
            payload=CORRUPT_PAYLOAD_TYPE_MISMATCH,
            schema=STRICT_SCHEMA,
        )
        types = [v["violation_type"] for v in result["violations"]]
        assert "TYPE_MISMATCH" in types
        assert result["overall_severity"] == "CRITICAL"


# ── schema_patcher tests ──────────────────────────────────────────────────────

class TestSchemaPatcher:
    def test_patch_removes_field_from_required(self):
        """patch_collection_schema should relax by removing a field from required."""
        from agent.tools.schema_patcher import patch_collection_schema

        mock_client = MagicMock()
        mock_db = mock_client["sentinel_demo"]
        mock_db.command.return_value = {"ok": 1.0}
        mock_db.list_collections.return_value = iter([
            {
                "name": "orders",
                "options": {"validator": {"$jsonSchema": STRICT_SCHEMA}},
            }
        ])

        with patch("agent.tools.schema_patcher.MongoClient", return_value=mock_client):
            result = patch_collection_schema(
                connection_string="mongodb://mock",
                database_name="sentinel_demo",
                collection_name="orders",
                fields_to_relax=["amount"],
                new_field_definitions={},
            )

        assert result["success"] is True
        assert "amount" in result["relaxed_fields"]
        # Ensure collMod was called (schema update issued)
        mock_db.command.assert_called_once()
        call_args = mock_db.command.call_args[0][0]
        assert call_args["collMod"] == "orders"
        assert "amount" not in call_args["validator"]["$jsonSchema"]["required"]


# ── quarantine_manager tests ──────────────────────────────────────────────────

class TestQuarantineManager:
    def test_quarantine_moves_document(self):
        """quarantine_corrupt_documents should move doc to shadow collection."""
        from agent.tools.quarantine_manager import quarantine_corrupt_documents

        doc_id = str(ObjectId())
        violations = [{"violation_type": "MISSING_REQUIRED_FIELD", "field": "amount"}]

        mock_client = MagicMock()
        mock_db = mock_client["sentinel_demo"]
        mock_source = MagicMock()
        mock_quarantine = MagicMock()

        # find_one returns the document
        mock_source.find_one.return_value = {**CORRUPT_PAYLOAD_MISSING_FIELD, "_id": ObjectId(doc_id)}
        mock_quarantine.insert_one.return_value = MagicMock(inserted_id=ObjectId())
        mock_source.delete_one.return_value = MagicMock(deleted_count=1)

        mock_db.__getitem__ = lambda self, name: (
            mock_source if name == "orders" else mock_quarantine
        )

        with patch("agent.tools.quarantine_manager.MongoClient", return_value=mock_client):
            result = quarantine_corrupt_documents(
                connection_string="mongodb://mock",
                database_name="sentinel_demo",
                collection_name="orders",
                document_ids=[doc_id],
                violations=violations,
            )

        assert result["total_attempted"] == 1
        # Insert to quarantine was attempted
        mock_quarantine.insert_one.assert_called_once()
        # Delete from source was attempted after successful insert
        mock_source.delete_one.assert_called_once()


# ── incident_reporter tests ───────────────────────────────────────────────────

class TestIncidentReporter:
    def test_report_contains_required_sections(self):
        """generate_incident_report should return all mandatory report fields."""
        from agent.tools.incident_reporter import generate_incident_report

        pipeline_trace = [
            {"step": "INSPECT",     "status": "completed", "details": "Schema with 5 required fields found."},
            {"step": "VALIDATE",    "status": "completed", "details": "2 violations detected."},
            {"step": "PATCH",       "status": "completed", "details": "Schema relaxed for 'amount'."},
            {"step": "QUARANTINE",  "status": "completed", "details": "2 documents moved."},
        ]

        result = generate_incident_report(
            collection_name="orders",
            database_name="sentinel_demo",
            violations_detected=2,
            documents_quarantined=2,
            schema_patched=True,
            pipeline_trace=pipeline_trace,
            final_status="CONTAINED",
        )

        assert "incident_id" in result
        assert "timestamp" in result
        assert "executive_summary" in result
        assert "pipeline_trace" in result
        assert "next_actions" in result
        assert result["final_status"] == "CONTAINED"
        assert result["violations_detected"] == 2
