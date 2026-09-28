from fastapi import FastAPI
from opentelemetry import trace

from app.telemetry import configure_telemetry, traced_span


def test_configure_telemetry_is_idempotent() -> None:
    app = FastAPI()
    configure_telemetry(app, service_name="civicpulse-backend-test", otlp_endpoint=None)
    configure_telemetry(app, service_name="civicpulse-backend-test", otlp_endpoint=None)
    # No exception on the second call is the behavior under test - a real
    # exporter/provider double-registration raises inside the SDK otherwise.


def test_traced_span_yields_a_recording_span() -> None:
    configure_telemetry(FastAPI(), service_name="civicpulse-backend-test", otlp_endpoint=None)
    with traced_span("test-span", provider="rules") as span:
        assert span.is_recording()
        assert isinstance(span, trace.Span)
