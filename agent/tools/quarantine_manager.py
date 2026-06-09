"""
Tool: quarantine_corrupt_documents
------------------------------------
Safely moves schema-violating documents out of the live collection and into
a shadow quarantine collection, stamped with full audit metadata.
Documents are NEVER deleted — they are preserved for manual remediation.
"""
from datetime import datetime, timezone
from pymongo import MongoClient
from bson import ObjectId
from agent.config import (
    MONGODB_CONNECTION_STRING,
    MONGODB_DATABASE,
    QUARANTINE_COLLECTION_SUFFIX,
)


def quarantine_corrupt_documents(
    connection_string: str = None,
    database_name: str = None,
    collection_name: str = None,
    document_ids: list = None,
    violations: list = None,
    remediation_hint: str = "",
) -> dict:
    """
    Moves corrupt documents to a quarantine shadow collection.

    Args:
        collection_name:   Source collection containing the corrupt documents.
        document_ids:      List of ObjectId strings to quarantine.
        violation_summary: Dict summarising the schema violations detected.
        remediation_hint:  Human-readable suggested fix for the reviewer.

    Returns:
        dict with keys:
          - quarantined_count (int)
          - failed_count (int)
          - quarantine_collection (str): name of the shadow collection
          - quarantined_ids (list[str])
          - failures (list[dict]): {id, error} for any failed moves
    """
    conn = connection_string or MONGODB_CONNECTION_STRING
    db_name = database_name or MONGODB_DATABASE

    client = MongoClient(conn)
    db = client[db_name]

    source_coll = db[collection_name]
    quarantine_coll_name = f"{collection_name}{QUARANTINE_COLLECTION_SUFFIX}"
    quarantine_coll = db[quarantine_coll_name]

    quarantined: list[str] = []
    failures: list[dict] = []

    for doc_id_str in (document_ids or []):
        try:
            oid = ObjectId(doc_id_str)
            doc = source_coll.find_one({"_id": oid})
            if not doc:
                failures.append({"id": doc_id_str, "error": "Document not found in source collection"})
                continue

            # Stamp the quarantine entry with full audit trail
            quarantine_entry = {
                **doc,
                "_sentinel_metadata": {
                    "quarantined_at": datetime.now(timezone.utc).isoformat(),
                    "source_collection": collection_name,
                    "quarantine_collection": quarantine_coll_name,
                    "violation_summary": violations,
                    "remediation_hint": remediation_hint or "Review schema mismatch and re-insert corrected document.",
                    "status": "PENDING_REMEDIATION",
                    "agent_version": "SENTINEL v1.0",
                },
            }

            quarantine_coll.insert_one(quarantine_entry)
            source_coll.delete_one({"_id": oid})
            quarantined.append(doc_id_str)

        except Exception as exc:
            failures.append({"id": doc_id_str, "error": str(exc)})

    client.close()

    total_attempted = len(document_ids or [])
    return {
        "total_attempted": total_attempted,
        "quarantined_count": len(quarantined),
        "failed_count": len(failures),
        "quarantine_collection": quarantine_coll_name,
        "quarantined_ids": quarantined,
        "failures": failures,
    }
