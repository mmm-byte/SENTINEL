"""Tests for the core/sentinel/ re-export package."""
from __future__ import annotations

import importlib


def test_core_sentinel_imports():
    """Every re-export should resolve at import time."""
    mod = importlib.import_module("core.sentinel")
    for name in mod.__all__:
        importlib.import_module(f"core.sentinel.{name}")


def test_tools_canonical_aliases():
    from core.sentinel.tools import (
        validate_payload,
        inspect_schema,
        patch_schema,
        quarantine_documents,
        generate_report,
    )
    # Each canonical name must be callable (functions or classes are fine).
    for fn in (
        validate_payload,
        inspect_schema,
        patch_schema,
        quarantine_documents,
        generate_report,
    ):
        assert callable(fn)
