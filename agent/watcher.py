"""
SENTINEL — MongoDB Change Stream Watcher
=========================================
The always-on immune system.

Instead of waiting for an external alert, this module opens a
MongoDB Change Stream on one or more collections and automatically
triggers the SENTINEL 5-step pipeline the moment a corrupt document
is inserted or updated.

This transforms SENTINEL from a tool-you-invoke into a
never-sleeping database guardian.

Usage:
    python -m agent.watcher                    # watch all configured collections
    python -m agent.watcher orders,users       # watch specific collections

Env vars:
    MONGODB_CONNECTION_STRING  — Atlas SRV URI
    MONGODB_DATABASE           — Database name (default: sentinel_demo)
    SENTINEL_WATCH_COLLECTIONS — Comma-separated list (default: orders)
"""
import asyncio
import json
import logging
import os
import sys
from datetime import datetime, timezone

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")


async def watch_collection(collection_name: str, db) -> None:
    """
    Opens a Change Stream on `collection_name` and triggers
    the SENTINEL pipeline on every insert/update/replace.

    Args:
        collection_name: MongoDB collection to watch.
        db: Motor async database handle.
    """
    # Lazy import to avoid circular deps at module level
    from agent.main import run_sentinel

    logger.info("[watcher] 👁️  Watching collection: %s", collection_name)
    pipeline = [
        {"$match": {"operationType": {"$in": ["insert", "update", "replace"]}}}
    ]

    async with db[collection_name].watch(pipeline, full_document="updateLookup") as stream:
        async for change in stream:
            doc = change.get("fullDocument") or change.get("updateDescription", {})
            op = change.get("operationType", "unknown")
            doc_id = str(change.get("documentKey", {}).get("_id", "unknown"))

            logger.info(
                "[watcher] 🚨 Change detected | op=%s | collection=%s | doc_id=%s",
                op, collection_name, doc_id
            )

            if doc:
                try:
                    await run_sentinel(collection_name, doc)
                except Exception as exc:
                    logger.error(
                        "[watcher] SENTINEL pipeline failed for %s/%s: %s",
                        collection_name, doc_id, exc
                    )
            else:
                logger.warning("[watcher] Change event had no fullDocument, skipping")


async def watch_all(collection_names: list) -> None:
    """
    Watches multiple collections concurrently.
    Each collection gets its own Change Stream coroutine.
    """
    try:
        import motor.motor_asyncio as motor  # type: ignore
    except ImportError:
        logger.error(
            "[watcher] motor not installed — run: pip install motor"
        )
        return

    conn = os.environ.get("MONGODB_CONNECTION_STRING")
    db_name = os.environ.get("MONGODB_DATABASE", "sentinel_demo")

    if not conn:
        logger.error("[watcher] MONGODB_CONNECTION_STRING not set")
        return

    client = motor.AsyncIOMotorClient(conn)
    db = client[db_name]

    logger.info(
        "[watcher] 🛡️  SENTINEL watcher online | db=%s | collections=%s",
        db_name, collection_names
    )
    logger.info("[watcher] Press Ctrl+C to stop.")

    tasks = [watch_collection(name, db) for name in collection_names]
    await asyncio.gather(*tasks)


if __name__ == "__main__":
    if len(sys.argv) > 1:
        cols = [c.strip() for c in sys.argv[1].split(",")]
    else:
        env_cols = os.environ.get("SENTINEL_WATCH_COLLECTIONS", "orders")
        cols = [c.strip() for c in env_cols.split(",")]

    try:
        asyncio.run(watch_all(cols))
    except KeyboardInterrupt:
        logger.info("[watcher] Stopped by user.")
