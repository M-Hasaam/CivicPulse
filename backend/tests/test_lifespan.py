import pytest
from fastapi.testclient import TestClient

from app.cache import client as redis_module
from app.main import app


def test_lifespan_opens_clients_on_startup_and_closes_them_on_shutdown(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    disposed: list[bool] = []

    class FakeEngine:
        async def dispose(self) -> None:
            disposed.append(True)

    monkeypatch.setattr("app.main.engine", FakeEngine())

    with TestClient(app):
        assert redis_module.redis_client() is not None  # created on the serving loop
        http_client = app.state.http_client
        assert not http_client.is_closed
        assert app.state.triage.provider.name  # provider chosen once, at startup

    assert http_client.is_closed
    with pytest.raises(RuntimeError, match="not initialised"):
        redis_module.redis_client()
    assert disposed == [True]
