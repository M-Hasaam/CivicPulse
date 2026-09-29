import pytest
from fastapi import FastAPI

from app.telemetry import configure_tracing


def test_configure_tracing_is_a_noop_without_the_env_var(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("OTEL_EXPORTER_OTLP_ENDPOINT", raising=False)
    app = FastAPI()
    configure_tracing(app)  # must not raise, must not require Jaeger reachable


def test_configure_tracing_does_not_raise_when_configured(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://jaeger:4318")
    app = FastAPI()
    configure_tracing(app)  # exporter is created lazily; no network call happens here
