"""Tests for the publish_track.py script.

These tests verify that the script:
  * accepts a valid track slug
  * writes a README, .env.example, and the shared core
  * does not leak the scripts/ or tracks/ directories into the output
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
PUBLISH = ROOT / "scripts" / "publish_track.py"
TRACKS = ["mongodb", "arize", "elastic", "fivetran", "gitlab", "dynatrace"]


@pytest.mark.parametrize("slug", TRACKS)
def test_publish_track_runs(tmp_path, slug):
    out = tmp_path / f"sentinel-{slug}"
    result = subprocess.run(
        [sys.executable, str(PUBLISH), "--track", slug, "--out", str(out)],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0, f"publish failed: {result.stderr}"
    assert (out / "README.md").exists()
    assert (out / ".env.example").exists()
    assert (out / "agent" / "ui_server.py").exists()
    assert (out / "ui" / "cockpit" / "index.html").exists()
    # The publish scaffolding itself must not be in the output
    assert not (out / "scripts").exists()
    assert not (out / "tracks").exists()
    # Track-specific hero text must appear in the README
    readme = (out / "README.md").read_text()
    assert "SENTINEL" in readme
    assert slug.upper() in readme.upper() or slug.title() in readme


def test_publish_unknown_track(tmp_path):
    out = tmp_path / "sentinel-bogus"
    result = subprocess.run(
        [sys.executable, str(PUBLISH), "--track", "bogus", "--out", str(out)],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    assert result.returncode != 0
    assert "unknown track" in result.stderr
