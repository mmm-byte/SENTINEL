"""Per-track publishing script.

Usage:
    python scripts/publish_track.py --track mongodb --out /tmp/sentinel-mongodb

It generates a clean, judge-facing per-track repository by copying the
shared core engine, the SRE Control Cockpit, the track-specific README
and metadata, and a minimal `.env.example`. It does NOT copy unrelated
track folders, your local `.env`, or audit logs.
"""
from __future__ import annotations

import argparse
import os
import shutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT))

from scripts.track_meta import get  # noqa: E402

# Files and directories copied verbatim into every track repo.
SHARED_PATHS = [
    "agent",
    "demo",
    "tests",
    "docs",
    "ui",
    "requirements.txt",
    "LICENSE",
    "README_METACOGNITION.md",
    "Tracks.txt",
    "Hackathon Details.txt",
]

# Files that should be regenerated per track.
PER_TRACK_FILES = [
    "README.md",
    ".env.example",
]


def copy_shared(out: Path) -> None:
    for rel in SHARED_PATHS:
        src = ROOT / rel
        if not src.exists():
            continue
        dst = out / rel
        if src.is_dir():
            shutil.copytree(src, dst, dirs_exist_ok=True, ignore=shutil.ignore_patterns(
                "__pycache__", ".pytest_cache", "*.pyc", ".env"
            ))
        else:
            shutil.copy2(src, dst)


def write_env_example(track, out: Path) -> None:
    lines = [
        "# SENTINEL environment variables (per-track)",
        f"# Track: {track.partner}",
        "",
        "# Audit + signing",
        "SENTINEL_AUDIT_LOG=./sentinel_audit.jsonl",
        "SENTINEL_HMAC_SIGNING_KEY=change-me-to-a-real-secret",
        "",
    ]
    if track.slug == "mongodb":
        lines += [
            "MONGODB_URI=mongodb://localhost:27017",
            "MONGODB_DATABASE=sentinel_demo",
        ]
    elif track.slug == "arize":
        lines += [
            "ARIZE_PHOENIX_API_KEY=",
            "ARIZE_PHOENIX_SPACE_ID=",
            "ARIZE_PHOENIX_ENDPOINT=",
        ]
    elif track.slug == "elastic":
        lines += [
            "ELASTIC_API_KEY=",
            "ELASTIC_ENDPOINT=https://your-cluster.es.us-central1.gcp.cloud.es.io",
        ]
    elif track.slug == "fivetran":
        lines += [
            "FIVETRAN_API_KEY=",
            "FIVETRAN_API_SECRET=",
        ]
    elif track.slug == "gitlab":
        lines += [
            "GITLAB_TOKEN=",
            "GITLAB_API_URL=https://gitlab.com/api/v4",
        ]
    elif track.slug == "dynatrace":
        lines += [
            "DYNATRACE_TOKEN=",
            "DYNATRACE_ENV=",
        ]
    (out / ".env.example").write_text("\n".join(lines) + "\n")


def write_readme(track, out: Path) -> None:
    title = track.title
    partner = track.partner
    one = track.one_liner
    body = f"""# {title}

> {one}

**Google Cloud Rapid Agent Hackathon 2026 · {partner} Partner Track**

---

## 🎯 The Problem

{track.story}

## 🤖 What SENTINEL Does

```
 ALERT RECEIVED
      │
      ▼
┌─────────────────────────────────────────────────────────────┐
│  Stage 1 (Dynatrace)  → INTAKE & ISOLATE                    │
│  Stage 2 (Elastic)    → TRIAGE LOGS                         │
│  Stage 3 (GitLab)     → REMEDIATE CODE                      │
│  Stage 4 ({partner:<8}) → {track.hero_stage.replace('_', ' ').upper():<27}        │
│  Stage 5 (Fivetran)   → RECONNECT PIPELINE                  │
│  Stage 6 (Arize)      → COGNITIVE ASSESS                    │
└─────────────────────────────────────────────────────────────┘
```

The `{track.hero_stage}` stage is the **hero** of this submission. It does
the work that makes this track stand out.

## ⚡ Quick Start

```bash
pip install -r requirements.txt
cp .env.example .env  # fill in your {partner} creds
python -m demo.run_full_demo
```

Then open the SRE Control Cockpit:

```bash
python -m agent.ui_server
# open http://127.0.0.1:8080
```

## 🧪 Tests

```bash
pytest tests/ -v
```

## 📦 Project Structure

See `docs/complete_plan.md` and `docs/implementation_plan.md` for the
full architecture. The shared core lives in `agent/`, the track-specific
overlay in this README, and the cockpit UI in `ui/cockpit/`.

## 🔐 Security & Governance

- Model Armor inspects every outbound and inbound JSON-RPC payload.
- All mutating calls are HMAC-SHA256 signed.
- Audit trail is append-only and machine-readable.
- Stage 4 schema changes require explicit human approval.
"""
    (out / "README.md").write_text(body)


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--track", required=True, help="track slug: mongodb | arize | elastic | fivetran | gitlab | dynatrace")
    p.add_argument("--out", required=True, help="output directory for the generated track repo")
    args = p.parse_args()

    track = get(args.track)
    out = Path(args.out).resolve()
    if out.exists():
        print(f"[publish] cleaning existing {out}")
        shutil.rmtree(out)
    out.mkdir(parents=True)

    print(f"[publish] generating {track.partner} track at {out}")
    copy_shared(out)
    write_env_example(track, out)
    write_readme(track, out)

    # Remove the publish script itself and the per-track scaffold directory
    # so the generated repo doesn't ship our scaffolding tools.
    for noise in ("scripts", "tracks"):
        noise_path = out / noise
        if noise_path.exists():
            shutil.rmtree(noise_path)

    print(f"[publish] done. Files in {out}:")
    for child in sorted(out.iterdir()):
        print(f"  - {child.name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
