"""
Demo: Inject Schema Drift into the 'orders' collection.
Simulates a bad application deployment that sends malformed payloads.

This creates the exact scenario SENTINEL is designed to catch:
  - order_id sent as integer instead of string  → TYPE_MISMATCH
  - 'amount' field missing entirely             → MISSING_REQUIRED_FIELD
  - unknown field 'discount_code' introduced    → violates additionalProperties

Run AFTER setup_demo_collection.py, BEFORE run_demo.py.

Usage:
    python -m demo.inject_schema_drift
"""
from pymongo import MongoClient
from agent.config import MONGODB_CONNECTION_STRING, MONGODB_DATABASE

# ── Corrupt payloads that will trigger SENTINEL ───────────────────────────────
CORRUPT_PAYLOADS = [
    {
        # TYPE_MISMATCH: order_id is int, schema expects string
        # MISSING_REQUIRED_FIELD: 'amount' is absent
        "order_id": 99999,               # ← BAD: should be "ORD-99999"
        "customer_name": "Dave Corrupt",
        # "amount": ???               ← BAD: missing required field
        "status": "pending",
        "created_at": "2026-06-08T12:35:00Z",
    },
    {
        # TYPE_MISMATCH: amount sent as string instead of double
        "order_id": "ORD-88888",
        "customer_name": "Eve Broken",
        "amount": "free",               # ← BAD: should be a float like 0.0
        "status": "pending",
        "created_at": "2026-06-08T12:36:00Z",
    },
]


def inject_drift():
    """
    Bypasses the MongoDB validator by using mongoclient directly with
    bypass_document_validation=True, simulating a service that sent bad data
    before validation was enforced, or a legacy write path.
    """
    client = MongoClient(MONGODB_CONNECTION_STRING)
    db = client[MONGODB_DATABASE]
    coll = db["orders"]

    print("💥 Injecting corrupt documents to simulate schema drift...")
    print()

    inserted_ids = []
    for i, payload in enumerate(CORRUPT_PAYLOADS, 1):
        result = coll.insert_one(
            payload,
            bypass_document_validation=True  # simulate legacy write path
        )
        inserted_ids.append(str(result.inserted_id))
        print(f"  [{i}] Injected corrupt document → _id: {result.inserted_id}")
        for field, value in payload.items():
            print(f"       {field}: {repr(value)}")
        print()

    print(f"⚠️  {len(inserted_ids)} corrupt document(s) now in 'orders' collection.")
    print()
    print("Corrupt document IDs (copy these for manual testing):")
    for oid in inserted_ids:
        print(f"  {oid}")

    print()
    print("✅ Schema drift injected. Run SENTINEL now:")
    print("   python -m demo.run_demo")
    print("   — or —")
    print("   adk web   (then paste the alert into the chat UI)")

    client.close()
    return inserted_ids


if __name__ == "__main__":
    inject_drift()
