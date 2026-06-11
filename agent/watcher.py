"""
SENTINEL Change Stream Watcher
================================
Makes SENTINEL always-on: listens to MongoDB Change Streams and
automatically triggers the full pipeline on every insert/update.

This is the difference between a tool you invoke and a system that
never sleeps.

Usage:
    python -m agent.watcher --collection orders
    python -m agent.watcher --collection orders --db sentinel_demo
"""
import argparse
import asyncio
import logging
import os

from dotenv import load_dotenv
load_dotenv()

from agent.observability import setup_observability
setup_observability()

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s [SENTINEL] %(levelname)s %(message)s")


async def watch_collection(
    collection_name: str,
    database_name: str = None,
    validate_only: bool = False,
) -> None:
    """
    Opens a MongoDB Change Stream on the given collection and invokes
    the SENTINEL pipeline on every insert/update/replace event.

    Args:
        collection_name: Collection to watch.
        database_name:   Database name (defaults to MONGODB_DATABASE env var).
        validate_only:   If True, only log violations without patching.
    """
    import pymongo  # type: ignore
    from agent.config import MONGODB_CONNECTION_STRING
    from agent.main import run_sentinel

    db_name = database_name or os.environ.get("MONGODB_DATABASE", "sentinel_demo")
    client = pymongo.MongoClient(MONGODB_CONNECTION_STRING)
    db = client[db_name]
    collection = db[collection_name]

    logger.info("🛡️  SENTINEL watching '%s.%s' via Change Stream...", db_name, collection_name)
    logger.info("   Press Ctrl+C to stop.")

    try:
        with collection.watch(
            pipeline=[
                {"$match": {"operationType": {"$in": ["insert", "update", "replace"]}}}
            ],
            full_document="updateLookup",
        ) as stream:
            async for change in _async_stream(stream):
                doc = change.get("fullDocument") or change.get("fullDocumentBeforeChange")
                op = change.get("operationType", "unknown")
                doc_id = change.get("documentKey", {}).get("_id", "unknown")

                if doc is None:
                    logger.warning("[watcher] %s event but no fullDocument — skipping", op)
                    continue

                logger.info("🚨 Change detected: op=%s doc_id=%s", op, doc_id)

                # Remove MongoDB internal fields before passing to SENTINEL
                clean_doc = {k: v for k, v in doc.items() if k != "_id"}

                try:
                    await run_sentinel(collection_name, clean_doc)
                except Exception as exc:
                    logger.error("[watcher] Pipeline error for doc %s: %s", doc_id, exc)

    except KeyboardInterrupt:
        logger.info("🛑 SENTINEL watcher stopped.")
    finally:
        client.close()


async def _async_stream(stream):
    """Async wrapper for synchronous pymongo change stream."""
    loop = asyncio.get_event_loop()
    while True:
        change = await loop.run_in_executor(None, lambda: next(stream, None))
        if change is None:
            break
        yield change


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="SENTINEL Change Stream Watcher")
    parser.add_argument("--collection", default="orders",
                        help="MongoDB collection to watch")
    parser.add_argument("--db", default=None,
                        help="MongoDB database name")
    args = parser.parse_args()

    asyncio.run(watch_collection(args.collection, args.db))
