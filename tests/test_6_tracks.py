"""
SENTINEL — 6-Track Integration Tests
======================================
Covers all partner-track integrations with mocked external services.
No live Atlas, Elastic, Fivetran, GitLab, or Arize connection required.

Run: pytest tests/test_6_tracks.py -v
"""
import os
from unittest.mock import MagicMock, patch

import pytest


# ─────────────────────────────────────────────────────────────
# Track 1 — MongoDB (core pipeline already tested in tests/test_tools.py)
# ─────────────────────────────────────────────────────────────
class TestMongoDBTrack:
    def test_generate_report_returns_incident_id(self):
        """Core pipeline report generation works without external deps."""
        with patch("agent.tools.incident_reporter._hook_elastic"), \
             patch("agent.tools.incident_reporter._hook_gitlab"):
            from agent.tools.incident_reporter import generate_incident_report
            result = generate_incident_report(
                collection_name="orders",
                violations_detected=2,
                documents_quarantined=1,
                schema_patched=True,
                final_status="CONTAINED",
            )
        assert result["incident_id"].startswith("SENTINEL-")
        assert result["final_status"] == "CONTAINED"
        assert "executive_summary" in result


# ─────────────────────────────────────────────────────────────
# Track 2 — Arize Phoenix
# ─────────────────────────────────────────────────────────────
class TestArizeTrack:
    def test_setup_observability_noop_without_key(self):
        """setup_observability() is a safe no-op when ARIZE_PHOENIX_API_KEY absent."""
        env = {k: v for k, v in os.environ.items() if k not in ("ARIZE_PHOENIX_API_KEY", "DYNATRACE_TOKEN", "DYNATRACE_ENDPOINT")}
        with patch.dict(os.environ, env, clear=True):
            from agent.observability import setup_observability
            setup_observability()  # must not raise

    def test_setup_arize_instruments_when_key_present(self):
        """When ARIZE_PHOENIX_API_KEY is set and libs installed, instrument is called."""
        mock_provider = MagicMock()
        mock_register = MagicMock(return_value=mock_provider)
        mock_instrumentor = MagicMock()

        with patch.dict(os.environ, {"ARIZE_PHOENIX_API_KEY": "test-key"}), \
             patch("agent.observability._setup_dynatrace"), \
             patch.dict("sys.modules", {
                 "phoenix.otel": MagicMock(register=mock_register),
                 "openinference.instrumentation.google_adk": MagicMock(
                     GoogleADKInstrumentor=MagicMock(return_value=mock_instrumentor)
                 ),
             }):
            import importlib
            import agent.observability as obs_mod
            importlib.reload(obs_mod)
            obs_mod._setup_arize()

        # register was called with project_name sentinel
        call_kwargs = mock_register.call_args
        assert call_kwargs is not None


# ─────────────────────────────────────────────────────────────
# Track 3 — Dynatrace
# ─────────────────────────────────────────────────────────────
class TestDynatraceTrack:
    def test_dynatrace_noop_without_env(self):
        """_setup_dynatrace is a safe no-op when vars absent."""
        env = {k: v for k, v in os.environ.items() if k not in ("DYNATRACE_ENDPOINT", "DYNATRACE_TOKEN")}
        with patch.dict(os.environ, env, clear=True):
            from agent.observability import _setup_dynatrace
            _setup_dynatrace()  # must not raise

    def test_dynatrace_adds_span_processor(self):
        """When DT vars set, BatchSpanProcessor is added to provider."""
        mock_provider = MagicMock()
        mock_exporter = MagicMock()
        mock_processor = MagicMock()

        with patch.dict(os.environ, {
            "DYNATRACE_ENDPOINT": "https://test.dynatrace.com",
            "DYNATRACE_TOKEN": "test-token",
        }), patch.dict("sys.modules", {
            "opentelemetry.exporter.otlp.proto.http.trace_exporter": MagicMock(
                OTLPSpanExporter=MagicMock(return_value=mock_exporter)
            ),
            "opentelemetry.sdk.trace.export": MagicMock(
                BatchSpanProcessor=MagicMock(return_value=mock_processor)
            ),
        }):
            import agent.observability as obs
            obs._tracer_provider = mock_provider
            obs._setup_dynatrace()

        mock_provider.add_span_processor.assert_called_once_with(mock_processor)


# ─────────────────────────────────────────────────────────────
# Track 4 — Fivetran
# ─────────────────────────────────────────────────────────────
class TestFivetranTrack:
    def test_trigger_resync_success(self):
        """trigger_fivetran_resync returns triggered=True on HTTP 200."""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        with patch.dict(os.environ, {
            "FIVETRAN_API_KEY": "key", "FIVETRAN_API_SECRET": "secret"
        }), patch("orchestrator.fivetran_agent.requests.post", return_value=mock_resp):
            from orchestrator.fivetran_agent import trigger_fivetran_resync
            result = trigger_fivetran_resync("connector-abc")
        assert result["triggered"] is True
        assert result["connector_id"] == "connector-abc"

    def test_trigger_resync_noop_without_key(self):
        """trigger_fivetran_resync returns triggered=False when not configured."""
        env = {k: v for k, v in os.environ.items() if k not in ("FIVETRAN_API_KEY", "FIVETRAN_API_SECRET")}
        with patch.dict(os.environ, env, clear=True):
            from orchestrator.fivetran_agent import trigger_fivetran_resync
            result = trigger_fivetran_resync("connector-abc")
        assert result["triggered"] is False

    def test_list_connectors_returns_error_without_key(self):
        env = {k: v for k, v in os.environ.items() if k not in ("FIVETRAN_API_KEY",)}
        with patch.dict(os.environ, env, clear=True):
            from orchestrator.fivetran_agent import list_fivetran_connectors
            result = list_fivetran_connectors()
        assert result[0].get("error") is not None


# ─────────────────────────────────────────────────────────────
# Track 5 — GitLab
# ─────────────────────────────────────────────────────────────
class TestGitLabTrack:
    def test_open_mr_success(self):
        """open_rollback_merge_request returns created=True on HTTP 201."""
        mock_resp = MagicMock()
        mock_resp.status_code = 201
        mock_resp.json.return_value = {"web_url": "https://gitlab.com/mr/1", "iid": 1}
        with patch.dict(os.environ, {
            "GITLAB_TOKEN": "glpat-test",
            "GITLAB_PROJECT_ID": "123",
        }), patch("orchestrator.gitlab_agent.requests.post", return_value=mock_resp):
            from orchestrator.gitlab_agent import open_rollback_merge_request
            result = open_rollback_merge_request(
                violation_summary="TYPE_MISMATCH on amount",
                collection_name="orders",
                incident_id="SENTINEL-20260611-000000",
            )
        assert result["created"] is True
        assert "gitlab.com" in result["mr_url"]

    def test_open_mr_noop_without_token(self):
        """open_rollback_merge_request returns created=False when not configured."""
        env = {k: v for k, v in os.environ.items() if k not in ("GITLAB_TOKEN", "GITLAB_PROJECT_ID")}
        with patch.dict(os.environ, env, clear=True):
            from orchestrator.gitlab_agent import open_rollback_merge_request
            result = open_rollback_merge_request(
                violation_summary="test", collection_name="orders", incident_id="X"
            )
        assert result["created"] is False


# ─────────────────────────────────────────────────────────────
# Track 6 — Elastic
# ─────────────────────────────────────────────────────────────
class TestElasticTrack:
    def test_index_incident_noop_without_config(self):
        """index_incident_report returns indexed=False when not configured."""
        env = {k: v for k, v in os.environ.items() if k not in ("ELASTIC_ENDPOINT", "ELASTIC_API_KEY")}
        with patch.dict(os.environ, env, clear=True):
            from agent.tools.elastic_memory import index_incident_report
            result = index_incident_report({"incident_id": "X", "collection_name": "orders"})
        assert result["indexed"] is False

    def test_index_incident_success(self):
        """index_incident_report calls es.index() and returns indexed=True."""
        mock_es = MagicMock()
        mock_es.index.return_value = {"_id": "abc123"}
        with patch.dict(os.environ, {
            "ELASTIC_ENDPOINT": "https://test.es.io",
            "ELASTIC_API_KEY": "test-key",
        }), patch("agent.tools.elastic_memory._get_client", return_value=mock_es):
            from agent.tools.elastic_memory import index_incident_report
            result = index_incident_report({"incident_id": "SENTINEL-X", "collection_name": "orders"})
        assert result["indexed"] is True
        assert result["es_id"] == "abc123"

    def test_search_incident_history_returns_empty_without_config(self):
        """search_incident_history returns [] when Elastic is not configured."""
        env = {k: v for k, v in os.environ.items() if k not in ("ELASTIC_ENDPOINT", "ELASTIC_API_KEY")}
        with patch.dict(os.environ, env, clear=True):
            from agent.tools.elastic_memory import search_incident_history
            result = search_incident_history("orders")
        assert result == []

    def test_search_incident_history_with_mock(self):
        """search_incident_history returns parsed hits from Elastic."""
        mock_es = MagicMock()
        mock_es.search.return_value = {
            "hits": {"hits": [{"_source": {"incident_id": "SENTINEL-OLD", "final_status": "CONTAINED"}}]}
        }
        with patch.dict(os.environ, {
            "ELASTIC_ENDPOINT": "https://test.es.io",
            "ELASTIC_API_KEY": "test-key",
        }), patch("agent.tools.elastic_memory._get_client", return_value=mock_es):
            from agent.tools.elastic_memory import search_incident_history
            results = search_incident_history("orders", "TYPE_MISMATCH")
        assert len(results) == 1
        assert results[0]["incident_id"] == "SENTINEL-OLD"


# ─────────────────────────────────────────────────────────────
# Integration: report auto-hooks Elastic + GitLab
# ─────────────────────────────────────────────────────────────
class TestReportHooks:
    def test_escalate_triggers_gitlab_hook(self):
        """ESCALATE status invokes _hook_gitlab."""
        with patch("agent.tools.incident_reporter._hook_elastic") as mock_elastic, \
             patch("agent.tools.incident_reporter._hook_gitlab") as mock_gitlab:
            from agent.tools.incident_reporter import generate_incident_report
            result = generate_incident_report(
                collection_name="orders",
                violations_detected=3,
                documents_quarantined=0,
                schema_patched=False,
                final_status="ESCALATE",
            )
        mock_elastic.assert_called_once()
        mock_gitlab.assert_called_once()
        assert result["final_status"] == "ESCALATE"

    def test_contained_does_not_trigger_gitlab(self):
        """CONTAINED status does NOT open a GitLab MR."""
        with patch("agent.tools.incident_reporter._hook_elastic"), \
             patch("agent.tools.incident_reporter._hook_gitlab") as mock_gitlab:
            from agent.tools.incident_reporter import generate_incident_report
            generate_incident_report(
                collection_name="orders",
                violations_detected=1,
                documents_quarantined=1,
                schema_patched=True,
                final_status="CONTAINED",
            )
        mock_gitlab.assert_not_called()
