"""OpenTelemetry tracing setup: one tracer provider for the whole process.

Auto-instruments FastAPI/httpx/asyncpg/redis; the one thing worth a manual
span is triage orchestration (services/triage_service.py), since that's the
domain event the trace exists to show, not just an HTTP call.
"""

from __future__ import annotations

import logging
from collections.abc import Iterator
from contextlib import contextmanager
from typing import TYPE_CHECKING, Any

from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
from opentelemetry.sdk.resources import SERVICE_NAME, Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

if TYPE_CHECKING:
    from fastapi import FastAPI

logger = logging.getLogger("civicpulse")

_configured = False


def configure_telemetry(app: "FastAPI", service_name: str, otlp_endpoint: str | None) -> None:
    """Wire up tracing once per process. Safe to call more than once."""
    global _configured
    if _configured:
        return
    _configured = True

    provider = TracerProvider(resource=Resource.create({SERVICE_NAME: service_name}))
    if otlp_endpoint:
        exporter = OTLPSpanExporter(endpoint=f"{otlp_endpoint}/v1/traces")
        provider.add_span_processor(BatchSpanProcessor(exporter))
    trace.set_tracer_provider(provider)

    FastAPIInstrumentor.instrument_app(app)
    HTTPXClientInstrumentor().instrument()
    try:
        from opentelemetry.instrumentation.asyncpg import AsyncPGInstrumentor

        AsyncPGInstrumentor().instrument()
    except Exception:
        logger.warning("asyncpg instrumentation unavailable, continuing without it")
    try:
        from opentelemetry.instrumentation.redis import RedisInstrumentor

        RedisInstrumentor().instrument()
    except Exception:
        logger.warning("redis instrumentation unavailable, continuing without it")


@contextmanager
def traced_span(name: str, **attributes: Any) -> Iterator[trace.Span]:
    tracer = trace.get_tracer("civicpulse")
    with tracer.start_as_current_span(name) as span:
        for key, value in attributes.items():
            span.set_attribute(key, value)
        yield span


def current_trace_id() -> str:
    """Hex trace id of the active span, or '-' if there is none (matches request_id's style)."""
    span = trace.get_current_span()
    ctx = span.get_span_context()
    if not ctx.is_valid:
        return "-"
    return format(ctx.trace_id, "032x")
