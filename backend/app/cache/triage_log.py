"""Shared triage observability in Redis: the last N outcomes and cache hit/miss
counts. Kept in Redis rather than process memory so every pod reports the same
numbers. Everything here fails soft - losing telemetry must never fail a request."""

import json
import logging
from typing import Any

from redis.asyncio import Redis
from redis.exceptions import RedisError

logger = logging.getLogger(__name__)

RECENT_KEY = "triage:recent"
RECENT_LIMIT = 20
HITS_KEY = "triage:cache:hits"
MISSES_KEY = "triage:cache:misses"


async def record_outcome(redis: Redis, outcome: dict[str, Any]) -> None:
    try:
        async with redis.pipeline(transaction=True) as pipe:
            pipe.lpush(RECENT_KEY, json.dumps(outcome))
            pipe.ltrim(RECENT_KEY, 0, RECENT_LIMIT - 1)
            await pipe.execute()
    except RedisError as exc:
        logger.warning("could not record triage outcome: %s", exc)


async def recent_outcomes(redis: Redis) -> list[dict[str, Any]]:
    try:
        return [json.loads(item) for item in await redis.lrange(RECENT_KEY, 0, RECENT_LIMIT - 1)]
    except RedisError as exc:
        logger.warning("could not read triage outcomes: %s", exc)
        return []


async def count_cache_lookup(redis: Redis, hit: bool) -> None:
    try:
        await redis.incr(HITS_KEY if hit else MISSES_KEY)
    except RedisError as exc:
        logger.warning("could not count triage cache lookup: %s", exc)


async def cache_counts(redis: Redis) -> tuple[int, int]:
    try:
        hits, misses = await redis.mget(HITS_KEY, MISSES_KEY)
    except RedisError as exc:
        logger.warning("could not read triage cache counts: %s", exc)
        return 0, 0
    return int(hits or 0), int(misses or 0)
