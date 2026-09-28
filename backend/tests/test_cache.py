import json

import pytest
from redis.asyncio import Redis
from redis.exceptions import ConnectionError as RedisConnectionError

from app.cache import stats_cache, triage_cache

pytestmark = pytest.mark.anyio


class BrokenRedis:
    """Stands in for a Redis that is down: every command fails."""

    async def get(self, *args: object, **kwargs: object) -> None:
        raise RedisConnectionError("redis down")

    set = delete = incr = get


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
    key = await stats_cache.current_stats_key(redis)
    ttl = await redis.ttl(key)
    assert stats_cache.STATS_TTL_SECONDS == 30  # the brief's 30 s TTL
    assert 0 < ttl <= 30


async def test_invalidate_forces_the_next_read_to_reload(redis: Redis) -> None:
    loader = Loader()
    await stats_cache.get_stats(redis, loader)
    await stats_cache.invalidate_stats(redis)
    fresh, state = await stats_cache.get_stats(redis, loader)

    assert state == stats_cache.MISS
    assert fresh == {"total_complaints": 32}  # reflects the write, not the stale entry


async def test_invalidate_moves_readers_to_a_new_key_rather_than_deleting_in_place(
    redis: Redis,
) -> None:
    key_before = await stats_cache.current_stats_key(redis)
    await stats_cache.invalidate_stats(redis)
    key_after = await stats_cache.current_stats_key(redis)
    assert key_before != key_after


async def test_current_stats_key_degrades_to_generation_0_on_a_bad_version(
    redis: Redis,
) -> None:
    """A manual redis-cli mistake setting the version to something non-numeric
    must not crash get_stats - fall back to generation 0 instead."""
    await redis.set(stats_cache.STATS_VERSION_KEY, "not-a-number")
    assert await stats_cache.current_stats_key(redis) == f"{stats_cache.STATS_KEY_PREFIX}:0"

    stats, state = await stats_cache.get_stats(redis, Loader())
    assert state == stats_cache.MISS  # answered, not crashed


async def test_a_corrupted_stats_entry_is_a_miss_not_a_crash(redis: Redis) -> None:
    key = await stats_cache.current_stats_key(redis)
    await redis.set(key, "not valid json{{{")

    loader = Loader()
    stats, state = await stats_cache.get_stats(redis, loader)
    assert state == stats_cache.MISS
    assert stats == {"total_complaints": 31}  # recomputed via the loader, not a crash
    assert loader.calls == 1


async def test_a_read_already_in_flight_when_invalidated_cannot_resurrect_stale_data(
    redis: Redis,
) -> None:
    """Reproduces the race Copilot flagged: a read's database query finishes
    (it captures the current key), then a write invalidates, then the read's
    now-stale result is written to the key it captured earlier. A later reader
    must never see that stale write."""
    loader = Loader()  # shared, so the second call visibly differs from the first
    key_read_captured = await stats_cache.current_stats_key(redis)
    stale_stats = await loader()  # as if this were the in-flight read's DB result

    await stats_cache.invalidate_stats(redis)  # a write commits and invalidates, mid-read

    # The in-flight read finally does its cache write, using the now-stale key.
    await redis.set(key_read_captured, json.dumps(stale_stats), ex=stats_cache.STATS_TTL_SECONDS)

    fresh, state = await stats_cache.get_stats(redis, loader)
    assert state == stats_cache.MISS
    assert fresh != stale_stats  # the post-invalidation reader re-queried instead


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


async def test_corrupted_or_wrong_shaped_cache_entries_are_a_miss_not_a_crash(
    redis: Redis,
) -> None:
    """A value that survives from an old cache format, a partial write, or a
    manual redis-cli mistake must not turn triage into a 500."""
    text = "Water pipe burst on Street 12"

    await redis.set(triage_cache.triage_key(text), "not valid json{{{")
    assert await triage_cache.get_cached_triage(redis, text) is None

    await redis.set(triage_cache.triage_key(text), json.dumps(["a", "json", "array"]))
    assert await triage_cache.get_cached_triage(redis, text) is None

    await redis.set(triage_cache.triage_key(text), json.dumps("just a string"))
    assert await triage_cache.get_cached_triage(redis, text) is None
