"""
Model Armor — the safety proxy that sits in front of every JSON-RPC call.

Why this exists
---------------
The `payload_validator.py` tool is a *payload-shape* validator (it checks
documents against MongoDB `$jsonSchema`). That is a different concern from
**trust-boundary safety**: stopping prompt-injection / dangerous verbs /
oversized payloads from ever crossing the orchestrator → partner boundary.

This module is the latter. It exposes two hooks called by the JSON-RPC client:

  * `inspect_outbound(method, params)` — pre-send. May raise `ArmorViolation`.
  * `inspect_inbound(method, result)`   — post-receive. May raise `ArmorViolation`.

It is intentionally small and dependency-free. In production it would be
replaced by the GCP Model Armor managed service; the interface here is
designed to be drop-in compatible with that migration.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Optional, Pattern


# ── exceptions ────────────────────────────────────────────────────────────────

class ArmorViolation(Exception):
    """Raised when an outbound or inbound payload violates a Model Armor policy."""

    def __init__(self, message: str, *, hook: str, rule: str, severity: str = "HIGH"):
        super().__init__(message)
        self.hook = hook          # "outbound" or "inbound"
        self.rule = rule          # which rule was violated
        self.severity = severity  # LOW | MEDIUM | HIGH | CRITICAL


# ── policy definition ─────────────────────────────────────────────────────────

@dataclass
class ArmorPolicy:
    """A configurable set of Model Armor rules.

    Defaults are intentionally conservative — every orchestrator call must
    pass them. Tweak via the constructor for production.
    """

    max_param_bytes: int = 64 * 1024               # 64 KB hard cap
    max_string_field_length: int = 4096            # per-string cap
    denylist_substrings: List[str] = field(default_factory=lambda: [
        # dangerous verbs that should never appear in free-text params
        "drop table", "drop database", "rm -rf", "delete from",
        "shutdown", "halt", "poweroff",
    ])
    denylist_regex: List[Pattern] = field(default_factory=lambda: [
        # prompt-injection heuristic: "ignore previous instructions" patterns
        re.compile(r"ignore\s+(all\s+)?previous\s+instructions", re.IGNORECASE),
        re.compile(r"disregard\s+(all\s+)?(prior|above)\s+(rules|instructions)", re.IGNORECASE),
        re.compile(r"you\s+are\s+now\s+(a|an)\s+", re.IGNORECASE),
        re.compile(r"<\s*script\s*>", re.IGNORECASE),     # XSS-ish in text fields
    ])
    allow_method_prefixes: Iterable[str] = field(default_factory=lambda: ("mcp.",))
    allow_actions: Iterable[str] = field(default_factory=lambda: (
        "query_topology", "search_logs", "query_blame", "create_branch",
        "create_merge_request", "collMod", "quarantine", "adjust_connector",
        "trigger_resync", "ingest_and_score", "get_report",
    ))

    def is_action_allowed(self, action: str) -> bool:
        return action in set(self.allow_actions)


# ── the armor itself ──────────────────────────────────────────────────────────

class ModelArmor:
    """Pre-send and post-receive policy enforcement."""

    def __init__(self, policy: Optional[ArmorPolicy] = None):
        self.policy = policy or ArmorPolicy()
        self.violations_log: List[Dict[str, Any]] = []  # in-memory audit

    # ── size checks ──────────────────────────────────────────────────────────
    def _check_size(self, params: Dict[str, Any], hook: str) -> None:
        try:
            import json
            size = len(json.dumps(params, default=str).encode("utf-8"))
        except (TypeError, ValueError):
            return  # non-serializable, will fail downstream — not our problem
        if size > self.policy.max_param_bytes:
            raise ArmorViolation(
                f"payload too large: {size} bytes > {self.policy.max_param_bytes}",
                hook=hook, rule="max_param_bytes", severity="HIGH",
            )

    def _walk_strings(self, obj: Any, hook: str) -> None:
        """Recursively enforce per-string length + denylist rules."""
        if isinstance(obj, dict):
            for k, v in obj.items():
                if isinstance(k, str):
                    self._check_string(k, hook)
                self._walk_strings(v, hook)
        elif isinstance(obj, list):
            for item in obj:
                self._walk_strings(item, hook)
        elif isinstance(obj, str):
            self._check_string(obj, hook)

    def _walk_strings_inbound(self, obj: Any, hook: str) -> None:
        """Inbound-only walker: enforce per-string length but skip denylist checks."""
        if isinstance(obj, dict):
            for k, v in obj.items():
                if isinstance(k, str):
                    self._check_string_length(k, hook)
                self._walk_strings_inbound(v, hook)
        elif isinstance(obj, list):
            for item in obj:
                self._walk_strings_inbound(item, hook)
        elif isinstance(obj, str):
            self._check_string_length(obj, hook)

    def _check_string_length(self, s: str, hook: str) -> None:
        if len(s) > self.policy.max_string_field_length:
            raise ArmorViolation(
                f"string field too long ({len(s)} chars)",
                hook=hook, rule="max_string_field_length", severity="MEDIUM",
            )

    def _check_string(self, s: str, hook: str) -> None:
        if len(s) > self.policy.max_string_field_length:
            raise ArmorViolation(
                f"string field too long ({len(s)} chars)",
                hook=hook, rule="max_string_field_length", severity="MEDIUM",
            )
        lower = s.lower()
        for bad in self.policy.denylist_substrings:
            if bad in lower:
                ev = ArmorViolation(
                    f"denylisted substring detected: '{bad}'",
                    hook=hook, rule="denylist_substrings", severity="CRITICAL",
                )
                # log the violation for tooling that calls inspect_outbound directly
                self.violations_log.append({"hook": hook, "rule": ev.rule, "severity": ev.severity})
                raise ev
        for pat in self.policy.denylist_regex:
            if pat.search(s):
                ev = ArmorViolation(
                    f"denylisted regex matched: {pat.pattern!r}",
                    hook=hook, rule="denylist_regex", severity="CRITICAL",
                )
                self.violations_log.append({"hook": hook, "rule": ev.rule, "severity": ev.severity})
                raise ev

    # ── public hooks ─────────────────────────────────────────────────────────
    def inspect_outbound(self, method: str, params: Dict[str, Any]) -> None:
        """Pre-send hook. Raises `ArmorViolation` on policy breach."""
        if not any(method.startswith(p) for p in self.policy.allow_method_prefixes):
            ev = ArmorViolation(
                f"method '{method}' not in allow-list",
                hook="outbound", rule="allow_method_prefixes", severity="CRITICAL",
            )
            self.violations_log.append({"hook": "outbound", "rule": ev.rule, "severity": ev.severity})
            raise ev

        # Per-action allow-list is only enforced when params declare an action.
        action = (params or {}).get("action")
        if action is not None and not self.policy.is_action_allowed(action):
            ev = ArmorViolation(
                f"action '{action}' not in allow-list",
                hook="outbound", rule="allow_actions", severity="HIGH",
            )
            self.violations_log.append({"hook": "outbound", "rule": ev.rule, "severity": ev.severity})
            raise ev

        self._check_size(params, hook="outbound")
        self._walk_strings(params, hook="outbound")

    def inspect_inbound(self, method: str, result: Any) -> None:
        """Post-receive hook. Raises `ArmorViolation` on policy breach."""
        # Inbound checks are lighter: only size + string-length, no denylist
        # (the partner is trusted to not attack itself).
        try:
            self._check_size(result if isinstance(result, dict) else {"r": result}, hook="inbound")
        except ArmorViolation as e:
            self.violations_log.append({"hook": "inbound", "rule": e.rule, "method": method})
            raise
        if isinstance(result, (dict, list)):
            self._walk_strings_inbound(result, hook="inbound")

    def log_violation(self, exc: ArmorViolation, method: str) -> None:
        self.violations_log.append({
            "hook": exc.hook,
            "rule": exc.rule,
            "severity": exc.severity,
            "method": method,
        })
