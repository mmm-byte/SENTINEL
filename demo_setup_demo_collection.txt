"""
Demo Setup: Create the 'orders' collection with a strict $jsonSchema validator.
Run this ONCE before running inject_schema_drift.py or run_demo.py.

Usage:
    python -m demo.setup_demo_collection
"""
from pymongo import MongoClient
from agent.config import MONGODB_CONNECTION_STRING, MONGODB_DATABASE

STRICT_ORDERS_SCHEMA = {
    "$jsonSchema": {
        "bsonType": "object",
        "required": ["order_id", "customer_name", "amount", "status", "created_at"],
        "properties": {
            "order_id": {
                "bsonType": "string",
                "description": "Unique order identifier — must be a string like 'ORD-001'",
            },
            "customer_name": {
                "bsonType": "string",
                "description": "Full name of the customer",
            },
            "amount": {
                "bsonType": "double",
                "description": "Order total in USD as a float",
            },
            "status": {
                "bsonType": "string",
                "enum": ["pending", "confirmed", "shipped", "delivered", "cancelled"],
                "description": "Current order status",
            },
            "created_at": {
                "bsonType": "string",
                "description": "ISO 8601 timestamp string",
            },
            "items": {
                "bsonType": "array",
                "description": "Optional list of line items",
            },
        },
        "additionalProperties": False,
    }
}

SEED_DOCUMENTS = [
    {
        "order_id": "ORD-001",
        "customer_name": "Alice Johnson",
        "amount": 129.99,
        "status": "confirmed",
        "created_at": "2026-06-08T10:00:00Z",
        "items": [{"sku": "LAPTOP-X1", "qty": 1, "price": 129.99}],
    },
    {
        "order_id": "ORD-002",
        "customer_name": "Bob Smith",
        "amount": 49.50,
        "status": "pending",
        "created_at": "2026-06-08T11:30:00Z",
    },
    {
        "order_id": "ORD-003",
        "customer_name": "Carol White",
        "amount": 299.00,
        "status": "shipped",
        "created_at": "2026-06-08T09:15:00Z",
        "items": [{"sku": "MONITOR-4K", "qty": 1, "price": 299.00}],
    },
]


def setup_demo_collection():
    client = MongoClient(MONGODB_CONNECTION_STRING)
    db = client[MONGODB_DATABASE]

    # Drop existing collection to start fresh
    db.drop_collection("orders")
    print("✓ Dropped existing 'orders' collection (if any)")

    # Create with strict schema validator
    db.create_collection(
        "orders",
        validator=STRICT_ORDERS_SCHEMA,
        validationLevel="strict",
        validationAction="error",
    )
    print("✓ Created 'orders' collection with strict $jsonSchema validator")

    # Seed with valid documents
    result = db["orders"].insert_many(SEED_DOCUMENTS)
    print(f"✓ Seeded {len(result.inserted_ids)} valid documents")

    print("\n📋 Current schema requires:")
    for field in STRICT_ORDERS_SCHEMA["$jsonSchema"]["required"]:
        print(f"   • {field} (required)")

    print("\n✅ Demo collection ready! Run inject_schema_drift.py next.")
    client.close()


if __name__ == "__main__":
    setup_demo_collection()
