"""
SENTINEL Observability
=======================
Track 2: Arize Phoenix — tracing + self-introspection MCP
Track 3: Dynatrace — dual OTel export with SENTINEL-specific span attributes

Both are optional: if env vars are absent the module is a no-op so
the core pipeline never breaks in local / CI environments.

SENTINEL-specific span attributes added for Dynatrace WIN condition:
  sentinel.tool_name          — which SENTINEL tool ran
  sentinel.violation_count    — violations found
  sentinel.patch_strategy     — what patch was applied
  sentinel.resolution_status  — CONTAINED / ESCALATE / RESOLVED
  sentinel.collection_name    — affected MongoDB collection
  sentinel.quarantine_count   — docs moved to quarantine
"""
import logging
import os
from contextlib import contextmanager
from typing import Optional

logger = logging.getLogger(__name__)

# Module-level provider slot (populated by _setup_arize)
_tracer_provider = None
_tracer = None


def setup_observability() -> None:
    """
    Call once at agent startup. Registers OpenInference instrumentation
    for Google ADK and sets up dual OTel export:
      1. Arize Phoenix Cloud  — traces, evals, self-improvement loop
      2. Dynatrace            — token spend, latency, SENTINEL-specific KPIs
    """
    _setup_arize()
    _setup_dynatrace()
    _setup_sentinel_tracer()


@contextmanager
def sentinel_span(
    tool_name: str,
    collection_name: str = None,
    violation_count: int = None,
    patch_strategy: str = None,
    resolution_status: str = None,
    quarantine_count: int = None,
):
    """
    Context manager that wraps a SENTINEL pipeline step in an OTel span
    with SENTINEL-specific attributes for Dynatrace WIN condition.

    Usage:
        with sentinel_span("patch_collection_schema", collection_name="orders",
                           violation_count=2, patch_strategy="make_optional"):
            result = patch_collection_schema(...)
    """
    if _tracer is None:
        yield
        return

    with _tracer.start_as_current_span(f"sentinel.{tool_name}") as span:
        span.set_attribute("sentinel.tool_name", tool_name)
        if collection_name:
            span.set_attribute("sentinel.collection_name", collection_name)
        if violation_count is not None:
            span.set_attribute("sentinel.violation_count", violation_count)
        if patch_strategy:
            span.set_attribute("sentinel.patch_strategy", patch_strategy)
        if resolution_status:
            span.set_attribute("sentinel.resolution_status", resolution_status)
        if quarantine_count is not None:
            span.set_attribute("sentinel.quarantine_count", quarantine_count)
        yield span


# ── Arize Phoenix ──────────────────────────────────────────────────────────────
def _setup_arize() -> None:
    api_key = os.environ.get("ARIZE_PHOENIX_API_KEY")
    endpoint = os.environ.get(
        "ARIZE_PHOENIX_ENDPOINT", "https://app.phoenix.arize.com/v1/traces"
    )
    if not api_key:
        logger.debug("[observability] ARIZE_PHOENIX_API_KEY not set — skipping Arize tracing")
        return

    try:
        from phoenix.otel import register  # type: ignore
        from openinference.instrumentation.google_adk import GoogleADKInstrumentor  # type: ignore

        tracer_provider = register(
            project_name="sentinel",
            endpoint=endpoint,
            headers={"api_key": api_key},
        )
        GoogleADKInstrumentor().instrument(tracer_provider=tracer_provider)

        import agent.observability as _self
        _self._tracer_provider = tracer_provider

        logger.info("[observability] Arize Phoenix tracing active → %s", endpoint)
    except ImportError:
        logger.warning(
            "[observability] arize-phoenix-otel / openinference-instrumentation-google-adk "
            "not installed — run: pip install arize-phoenix-otel "
            "openinference-instrumentation-google-adk"
        )


# ── Dynatrace ──────────────────────────────────────────────────────────────────
def _setup_dynatrace() -> None:
    dt_endpoint = os.environ.get("DYNATRACE_ENDPOINT")
    dt_token = os.environ.get("DYNATRACE_TOKEN")
    if not dt_endpoint or not dt_token:
        logger.debug("[observability] DYNATRACE_ENDPOINT / DYNATRACE_TOKEN not set — skipping DT")
        return

    try:
        from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter  # type: ignore
        from opentelemetry.sdk.trace.export import BatchSpanProcessor  # type: ignore

        provider = _tracer_provider
        if provider is None:
            from opentelemetry.sdk.trace import TracerProvider  # type: ignore
            from opentelemetry.sdk.resources import Resource  # type: ignore
            provider = TracerProvider(
                resource=Resource.create({
                    "service.name": "sentinel",
                    "service.version": "1.0.0",
                    "deployment.environment": os.environ.get("ENVIRONMENT", "production"),
                })
            )

        dt_exporter = OTLPSpanExporter(
            endpoint=f"{dt_endpoint.rstrip('/')}/v1/traces",
            headers={"Authorization": f"Api-Token {dt_token}"},
        )
        provider.add_span_processor(BatchSpanProcessor(dt_exporter))
        logger.info("[observability] Dynatrace OTel export active → %s", dt_endpoint)
    except ImportError:
        logger.warning(
            "[observability] opentelemetry-exporter-otlp-proto-http not installed — "
            "run: pip install opentelemetry-exporter-otlp-proto-http"
        )


def _setup_sentinel_tracer() -> None:
    """Set up the SENTINEL-specific tracer for custom span attributes."""
    global _tracer
    try:
        from opentelemetry import trace  # type: ignore
        _tracer = trace.get_tracer("sentinel", "1.0.0")
        logger.debug("[observability] SENTINEL custom tracer ready")
    except ImportError:
        pass
