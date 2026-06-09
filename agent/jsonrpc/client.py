"""
SENTINEL JSON-RPC 2.0 client with:
  * Model Armor (outbound + inbound) policy hooks
  * HMAC-SHA256 request signing
  * Append-only signed audit log

Truthful design notes
---------------------
- HMAC signing is opt-in: pass `signing_key` to the constructor. If absent,
  no signature is computed but the call still works.
- The audit log is a plain JSONL file on disk by default (`./sentinel_audit.jsonl`).
  In production this would be Cloud Logging or a tamper-evident store.
- Backwards-compatible: existing call sites that pass only `(method, params)`
  continue to work — the new fields have sensible defaults.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import os
import time
import uuid
from typing import Any, Dict, Optional

import httpx

from agent.model_armor import ArmorViolation, ModelArmor


class JSONRPCError(Exception):
    pass


def _canonical(payload: Dict[str, Any]) -> str:
    """Deterministic JSON serialization for signing/hashing."""
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)


def _hash_params(params: Dict[str, Any]) -> str:
    return hashlib.sha256(_canonical(params).encode("utf-8")).hexdigest()


class JSONRPCClient:
    def __init__(
        self,
        endpoint: str,
        timeout: int = 10,
        *,
        agent_id: str = "agent-unknown",
        signing_key: Optional[str] = None,
        armor: Optional[ModelArmor] = None,
        audit_log_path: Optional[str] = None,
    ):
        self.endpoint = endpoint
        self.timeout = timeout
        self.agent_id = agent_id
        self.signing_key = signing_key.encode("utf-8") if signing_key else None
        self.armor = armor or ModelArmor()
        self.audit_log_path = audit_log_path or os.getenv(
            "SENTINEL_AUDIT_LOG", "./sentinel_audit.jsonl"
        )

    # ── public API ───────────────────────────────────────────────────────────
    def call_method(
        self,
        method: str,
        params: Dict[str, Any],
        id: Optional[str] = None,
        *,
        idempotency_key: Optional[str] = None,
    ) -> Any:
        request_id = id or str(uuid.uuid4())
        # enrich params with identity & idempotency so every call is traceable
        params = dict(params or {})
        params.setdefault("agent_id", self.agent_id)
        params.setdefault("idempotency_key", idempotency_key or str(uuid.uuid4()))

        payload = {
            "jsonrpc": "2.0",
            "id": request_id,
            "method": method,
            "params": params,
        }

        # ── pre-send: Model Armor ────────────────────────────────────────────
        try:
            self.armor.inspect_outbound(method, params)
        except ArmorViolation as e:
            self.armor.log_violation(e, method)
            self._audit(request_id, method, params, status="blocked_outbound", error=f"{e.__class__.__name__}: {e}")
            raise

        # ── sign ─────────────────────────────────────────────────────────────
        if self.signing_key is not None:
            payload["signature"] = self._sign(payload)

        # ── transport ────────────────────────────────────────────────────────
        t0 = time.time()
        try:
            resp = httpx.post(self.endpoint, json=payload, timeout=self.timeout)
        except Exception as e:
            self._audit(request_id, method, params, status="transport_error", error=str(e))
            raise JSONRPCError(f"transport error: {e}")

        if resp.status_code != 200:
            self._audit(request_id, method, params,
                        status=f"http_{resp.status_code}", error=resp.text)
            raise JSONRPCError(f"bad status: {resp.status_code} - {resp.text}")

        body = resp.json()
        if "error" in body:
            self._audit(request_id, method, params, status="rpc_error", error=str(body["error"]))
            raise JSONRPCError(body["error"])

        if "result" not in body:
            self._audit(request_id, method, params, status="invalid_response", error=str(body))
            raise JSONRPCError(f"invalid response: {body}")

        result = body["result"]
        duration_ms = int((time.time() - t0) * 1000)

        # ── post-receive: Model Armor ────────────────────────────────────────
        try:
            self.armor.inspect_inbound(method, result)
        except ArmorViolation as e:
            self.armor.log_violation(e, method)
            self._audit(request_id, method, params, status="blocked_inbound", error=f"{e.__class__.__name__}: {e}")
            raise

        self._audit(request_id, method, params,
                    status="ok", duration_ms=duration_ms, result_size=len(_canonical(result)))
        return result

    # ── signing ──────────────────────────────────────────────────────────────
    def _sign(self, payload: Dict[str, Any]) -> str:
        body = {k: v for k, v in payload.items() if k != "signature"}
        mac = hmac.new(self.signing_key, _canonical(body).encode("utf-8"), hashlib.sha256)
        return f"sha256={mac.hexdigest()}"

    # ── audit log ───────────────────────────────────────────────────────────
    def _audit(
        self,
        request_id: str,
        method: str,
        params: Dict[str, Any],
        *,
        status: str,
        duration_ms: Optional[int] = None,
        result_size: Optional[int] = None,
        error: Optional[str] = None,
    ) -> None:
        entry = {
            "request_id": request_id,
            "agent_id": self.agent_id,
            "method": method,
            "endpoint": self.endpoint,
            "params_hash": _hash_params(params),
            "status": status,
            "timestamp": time.time(),
        }
        if duration_ms is not None:
            entry["duration_ms"] = duration_ms
        if result_size is not None:
            entry["result_size_bytes"] = result_size
        if error is not None:
            entry["error"] = error

        # sign the entry so the audit trail itself is tamper-evident
        if self.signing_key is not None:
            entry["signature"] = "sha256=" + hmac.new(
                self.signing_key,
                _canonical(entry).encode("utf-8"),
                hashlib.sha256,
            ).hexdigest()

        try:
            with open(self.audit_log_path, "a", encoding="utf-8") as f:
                f.write(_canonical(entry) + "\n")
        except OSError:
            # audit failure must not break the call path
            pass

    # ── convenience: verify a signature on an inbound payload ───────────────
    def verify(self, payload: Dict[str, Any], signature: str) -> bool:
        if not self.signing_key:
            return False
        body = {k: v for k, v in payload.items() if k != "signature"}
        expected = "sha256=" + hmac.new(
            self.signing_key, _canonical(body).encode("utf-8"), hashlib.sha256
        ).hexdigest()
        return hmac.compare_digest(expected, signature or "")
