import pytest
from redis.asyncio import Redis
from redis.exceptions import ConnectionError as RedisConnectionError

from app.cache import stats_cache, triage_cache

pytestmark = pytest.mark.anyio


class BrokenRedis:
    """Stands in for a Redis that is down: every command fails."""

    async def get(self, *args: object, **kwargs: object) -> None:
        raise RedisConnectionError("redis down")

    set = delete = get


class Loader:
    """Counts how often the database would have been queried."""

    def __init__(self) -> None:
        self.calls = 0

    async def __call__(self) -> dict[str, int]:
        self.calls += 1
        return {"total_complaints": 30 + self.calls}


# --- stats cache -----------------------------------------------------------------------------


async def test_stats_first_read_is_a_miss_second_is_a_hit(redis: Redis) -> None:
    loader = Loader()
    first, first_state = await stats_cache.get_stats(redis, loader)
    second, second_state = await stats_cache.get_stats(redis, loader)

    assert (first_state, second_state) == (stats_cache.MISS, stats_cache.HIT)
    assert first == second == {"total_complaints": 31}
    assert loader.calls == 1  # the second read never reached the database


async def test_stats_entry_expires_via_ttl(redis: Redis) -> None:
    await stats_cache.get_stats(redis, Loader())
    ttl = await redis.ttl(stats_cache.STATS_KEY)
    assert 0 < ttl <= stats_cache.STATS_TTL_SECONDS


async def test_invalidate_forces_the_next_read_to_reload(redis: Redis) -> None:
    loader = Loader()
    await stats_cache.get_stats(redis, loader)
    await stats_cache.invalidate_stats(redis)
    fresh, state = await stats_cache.get_stats(redis, loader)

    assert state == stats_cache.MISS
    assert fresh == {"total_complaints": 32}  # reflects the write, not the stale entry


async def test_stats_bypass_the_cache_when_redis_is_down() -> None:
    loader = Loader()
    stats, state = await stats_cache.get_stats(BrokenRedis(), loader)  # type: ignore[arg-type]

    assert state == stats_cache.BYPASS
    assert stats == {"total_complaints": 31}  # still answered, straight from the loader


async def test_invalidate_never_raises_when_redis_is_down() -> None:
    await stats_cache.invalidate_stats(BrokenRedis())  # type: ignore[arg-type]


# --- triage cache ----------------------------------------------------------------------------

RESULT = {"category": "water", "priority": "high", "triaged_by": "groq"}


async def test_triage_miss_then_hit(redis: Redis) -> None:
    text = "Main water pipeline burst near Street 12"
    assert await triage_cache.get_cached_triage(redis, text) is None

    await triage_cache.cache_triage(redis, text, RESULT)
    assert await triage_cache.get_cached_triage(redis, text) == RESULT


async def test_triage_key_ignores_case_and_whitespace(redis: Redis) -> None:
    await triage_cache.cache_triage(redis, "Water pipe burst on Street 12", RESULT)
    cached = await triage_cache.get_cached_triage(redis, "  WATER pipe   burst on street 12 ")
    assert cached == RESULT


async def test_triage_different_text_is_a_miss(redis: Redis) -> None:
    await triage_cache.cache_triage(redis, "Water pipe burst on Street 12", RESULT)
    assert await triage_cache.get_cached_triage(redis, "Streetlight out on Street 9") is None


async def test_triage_entry_lives_24_hours(redis: Redis) -> None:
    text = "Water pipe burst on Street 12"
    await triage_cache.cache_triage(redis, text, RESULT)
    ttl = await redis.ttl(triage_cache.triage_key(text))
    assert 86_000 < ttl <= triage_cache.TRIAGE_TTL_SECONDS == 86_400


async def test_triage_cache_failures_degrade_to_a_miss() -> None:
    broken = BrokenRedis()
    assert await triage_cache.get_cached_triage(broken, "any text") is None  # type: ignore[arg-type]
    await triage_cache.cache_triage(broken, "any text", RESULT)  # type: ignore[arg-type]
