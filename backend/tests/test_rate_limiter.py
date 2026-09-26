from types import SimpleNamespace

import httpx
import pytest
from fastapi import Depends, FastAPI
from redis.asyncio import Redis
from redis.exceptions import ConnectionError as RedisConnectionError

from app.cache import rate_limiter
from app.cache.client import get_redis
from app.config import settings

pytestmark = pytest.mark.anyio


def freeze_time(monkeypatch: pytest.MonkeyPatch, now: float) -> SimpleNamespace:
    """Control the clock the limiter sees (only its own module, not Redis's expiry)."""
    clock = SimpleNamespace(now=now)
    monkeypatch.setattr(rate_limiter, "time", SimpleNamespace(time=lambda: clock.now))
    return clock


# --- check_rate_limit ------------------------------------------------------------------------


async def test_allows_up_to_the_limit_then_blocks(redis: Redis) -> None:
    results = [await rate_limiter.check_rate_limit(redis, "1.2.3.4", 3, 60) for _ in range(5)]
    assert results == [True, True, True, False, False]


async def test_clients_are_counted_independently(redis: Redis) -> None:
    for _ in range(3):
        await rate_limiter.check_rate_limit(redis, "1.1.1.1", 3, 60)

    assert await rate_limiter.check_rate_limit(redis, "1.1.1.1", 3, 60) is False
    assert await rate_limiter.check_rate_limit(redis, "2.2.2.2", 3, 60) is True


async def test_limit_resets_in_the_next_window(
    redis: Redis, monkeypatch: pytest.MonkeyPatch
) -> None:
    clock = freeze_time(monkeypatch, 1000.0)
    for _ in range(3):
        await rate_limiter.check_rate_limit(redis, "1.2.3.4", 3, 60)
    assert await rate_limiter.check_rate_limit(redis, "1.2.3.4", 3, 60) is False

    clock.now += 60  # next fixed window
    assert await rate_limiter.check_rate_limit(redis, "1.2.3.4", 3, 60) is True


async def test_counter_always_has_a_ttl(redis: Redis) -> None:
    await rate_limiter.check_rate_limit(redis, "1.2.3.4", 3, 60)
    keys = [key async for key in redis.scan_iter("ratelimit:*")]

    assert len(keys) == 1
    assert 0 < await redis.ttl(keys[0]) <= 60


async def test_fails_open_when_redis_is_down() -> None:
    class BrokenPipelineRedis:
        def pipeline(self, *args: object, **kwargs: object) -> None:
            raise RedisConnectionError("redis down")

    allowed = await rate_limiter.check_rate_limit(BrokenPipelineRedis(), "1.2.3.4", 3, 60)  # type: ignore[arg-type]
    assert allowed is True


# --- retry_after_seconds ---------------------------------------------------------------------


@pytest.mark.parametrize(
    ("now", "expected"),
    [(1000.0, 20), (1019.2, 1), (1020.0, 60), (1020.4, 60)],
    ids=["mid-window", "almost-over", "window-start", "just-after-start"],
)
def test_retry_after_is_seconds_left_in_the_window(
    monkeypatch: pytest.MonkeyPatch, now: float, expected: int
) -> None:
    freeze_time(monkeypatch, now)  # 1000 % 60 = 40, so 20s remain in the window
    assert rate_limiter.retry_after_seconds(60) == expected


# --- client_identifier -----------------------------------------------------------------------


def _request(headers: dict[str, str], client: tuple[str, int] | None) -> rate_limiter.Request:
    scope = {
        "type": "http",
        "headers": [(k.lower().encode(), v.encode()) for k, v in headers.items()],
        "client": client,
    }
    return rate_limiter.Request(scope)


def test_client_identifier_prefers_first_forwarded_address() -> None:
    request = _request({"X-Forwarded-For": "203.0.113.7, 10.0.0.2"}, ("10.0.0.2", 5000))
    assert rate_limiter.client_identifier(request) == "203.0.113.7"


def test_client_identifier_falls_back_to_the_socket_address() -> None:
    assert rate_limiter.client_identifier(_request({}, ("198.51.100.4", 5000))) == "198.51.100.4"
    assert rate_limiter.client_identifier(_request({}, None)) == "unknown"


# --- the dependency over real HTTP -----------------------------------------------------------


@pytest.fixture
async def api(redis: Redis, monkeypatch: pytest.MonkeyPatch) -> httpx.AsyncClient:
    monkeypatch.setattr(settings, "RATE_LIMIT_MAX_REQUESTS", 3)
    monkeypatch.setattr(settings, "RATE_LIMIT_WINDOW_SECONDS", 60)

    app = FastAPI()
    app.dependency_overrides[get_redis] = lambda: redis

    @app.post("/api/complaints", dependencies=[Depends(rate_limiter.enforce_rate_limit)])
    async def create() -> dict[str, bool]:
        return {"ok": True}

    return httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test")


async def test_over_the_limit_gets_429_with_retry_after(api: httpx.AsyncClient) -> None:
    headers = {"X-Forwarded-For": "203.0.113.7"}
    statuses = [(await api.post("/api/complaints", headers=headers)).status_code for _ in range(3)]
    assert statuses == [200, 200, 200]

    blocked = await api.post("/api/complaints", headers=headers)
    assert blocked.status_code == 429
    assert 1 <= int(blocked.headers["Retry-After"]) <= 60
    assert "Too many requests" in blocked.json()["detail"]


async def test_one_client_being_blocked_does_not_affect_another(api: httpx.AsyncClient) -> None:
    for _ in range(4):
        await api.post("/api/complaints", headers={"X-Forwarded-For": "203.0.113.7"})

    other = await api.post("/api/complaints", headers={"X-Forwarded-For": "198.51.100.9"})
    assert other.status_code == 200
