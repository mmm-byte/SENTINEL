"""
SENTINEL Observability
=======================
Dual OTel export to Arize Phoenix (traces + self-introspection MCP)
and Dynatrace (token spend, tool call latency, error rates).

Both are optional: if env vars are absent the module is a no-op so
the core pipeline never breaks in local / CI environments.
"""
import logging
import os

logger = logging.getLogger(__name__)


def setup_observability() -> None:
    """
    Call once at agent startup. Registers OpenInference instrumentation
    for Google ADK and sets up dual OTel export:
      1. Arize Phoenix Cloud  — traces, evals, self-improvement loop
      2. Dynatrace            — token spend, latency, error dashboards
    """
    _setup_arize()
    _setup_dynatrace()


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

        # Store tracer_provider globally so Dynatrace can attach a second exporter
        import agent.observability as _self
        _self._tracer_provider = tracer_provider

        logger.info("[observability] Arize Phoenix tracing active → %s", endpoint)
    except ImportError:
        logger.warning(
            "[observability] arize-phoenix-otel / openinference-instrumentation-google-adk "
            "not installed — run: pip install arize-phoenix-otel "
            "openinference-instrumentation-google-adk"
        )


# Module-level provider slot (populated by _setup_arize)
_tracer_provider = None


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
            # Arize not configured — create a standalone provider
            from opentelemetry.sdk.trace import TracerProvider  # type: ignore
            from opentelemetry.sdk.resources import Resource  # type: ignore
            provider = TracerProvider(
                resource=Resource.create({"service.name": "sentinel"})
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
