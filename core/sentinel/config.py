"""SENTINEL core configuration. Mirrors the existing `agent/config.py`."""
from __future__ import annotations

import os


# ── Gemini / Google Cloud ──────────────────────────────────────────────────────
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.0-flash-exp")
GOOGLE_CLOUD_PROJECT = os.getenv("GOOGLE_CLOUD_PROJECT", "")
GOOGLE_CLOUD_LOCATION = os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", "")

# Approvals
AUTO_APPROVE_SCHEMA_CHANGES = os.getenv("AUTO_APPROVE_SCHEMA_CHANGES", "false").lower() in ("1", "true", "yes")

# ── Partner endpoints (override per track) ────────────────────────────────────
ARIZE_PHOENIX_API_KEY = os.getenv("ARIZE_PHOENIX_API_KEY")
ARIZE_PHOENIX_SPACE_ID = os.getenv("ARIZE_PHOENIX_SPACE_ID")
ARIZE_PHOENIX_ENDPOINT = os.getenv("ARIZE_PHOENIX_ENDPOINT")

FIVETRAN_API_KEY = os.getenv("FIVETRAN_API_KEY")
FIVETRAN_API_SECRET = os.getenv("FIVETRAN_API_SECRET")

ELASTIC_API_KEY = os.getenv("ELASTIC_API_KEY")
ELASTIC_ENDPOINT = os.getenv("ELASTIC_ENDPOINT")

GITLAB_TOKEN = os.getenv("GITLAB_TOKEN")
GITLAB_API_URL = os.getenv("GITLAB_API_URL", "https://gitlab.com/api/v4")

DYNATRACE_TOKEN = os.getenv("DYNATRACE_TOKEN")
DYNATRACE_ENV = os.getenv("DYNATRACE_ENV")

MONGODB_URI = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
MONGODB_DATABASE = os.getenv("MONGODB_DATABASE", "sentinel_demo")

# ── Audit & signing ───────────────────────────────────────────────────────────
SENTINEL_AUDIT_LOG = os.getenv("SENTINEL_AUDIT_LOG", "./sentinel_audit.jsonl")
SENTINEL_HMAC_SIGNING_KEY = os.getenv("SENTINEL_HMAC_SIGNING_KEY", "change-me-to-a-real-secret")
