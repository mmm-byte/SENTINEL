"""
SENTINEL Configuration
Loads environment variables from .env for all agent components.
"""
import os
from dotenv import load_dotenv

load_dotenv()

# ── MongoDB ────────────────────────────────────────────────────────────────────
MONGODB_CONNECTION_STRING = os.getenv(
    "MONGODB_CONNECTION_STRING", "mongodb://localhost:27017"
)
MONGODB_DATABASE = os.getenv("MONGODB_DATABASE", "sentinel_demo")
QUARANTINE_COLLECTION_SUFFIX = "_quarantine"

# ── Gemini / Google Cloud ──────────────────────────────────────────────────────
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.0-flash-exp")
GOOGLE_CLOUD_PROJECT = os.getenv("GOOGLE_CLOUD_PROJECT", "")
GOOGLE_CLOUD_LOCATION = os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", "")          # AI Studio fallback
