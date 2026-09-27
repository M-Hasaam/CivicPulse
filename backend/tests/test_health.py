import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.routes import health

client = TestClient(app)


async def _ok() -> None:
    return None


async def _unreachable() -> None:
    raise ConnectionRefusedError("postgres down")


def test_health_is_alive_without_touching_the_database(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(health, "ping_database", _unreachable)
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "probe": "liveness"}


def test_ready_returns_200_when_postgres_and_redis_are_reachable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(health, "ping_database", _ok)
    monkeypatch.setattr(health, "ping_redis", _ok)
    response = client.get("/ready")
    assert response.status_code == 200
    assert response.json() == {"status": "ready"}


def test_ready_returns_503_naming_postgres_when_unreachable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(health, "ping_database", _unreachable)
    monkeypatch.setattr(health, "ping_redis", _ok)
    response = client.get("/ready")
    assert response.status_code == 503
    assert response.json()["failed_dependencies"] == ["postgres (ConnectionRefusedError)"]


def test_ready_returns_503_naming_redis_when_unreachable(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(health, "ping_database", _ok)
    monkeypatch.setattr(health, "ping_redis", _unreachable)
    response = client.get("/ready")
    assert response.status_code == 503
    assert response.json()["failed_dependencies"] == ["redis (ConnectionRefusedError)"]


def test_ready_names_every_failed_dependency(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(health, "ping_database", _unreachable)
    monkeypatch.setattr(health, "ping_redis", _unreachable)
    response = client.get("/ready")
    assert response.status_code == 503
    assert response.json()["failed_dependencies"] == [
        "postgres (ConnectionRefusedError)",
        "redis (ConnectionRefusedError)",
    ]


def test_metrics_exposes_request_counter() -> None:
    client.get("/health")
    response = client.get("/metrics")
    assert response.status_code == 200
    assert "civicpulse_http_requests_total" in response.text


def test_metrics_label_unknown_paths_without_growing_series() -> None:
    client.get("/no-such-page-12345")
    response = client.get("/metrics")
    assert "no-such-page-12345" not in response.text
    assert 'endpoint="unmatched"' in response.text
