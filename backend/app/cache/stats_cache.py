import json
import logging
from collections.abc import Awaitable, Callable
from typing import Any

from redis.asyncio import Redis
from redis.exceptions import RedisError

logger = logging.getLogger(__name__)

STATS_KEY = "cache:stats"
STATS_TTL_SECONDS = 60

# Values for the X-Cache response header.
HIT = "HIT"
MISS = "MISS"
BYPASS = "BYPASS"  # Redis unavailable: answered straight from the database


async def get_stats(
    redis: Redis, loader: Callable[[], Awaitable[dict[str, Any]]]
) -> tuple[dict[str, Any], str]:
    """Read-through cache: return (stats, X-Cache value).

    A cache outage must never take the endpoint down, so any Redis error falls
    back to computing the stats directly.
    """
    try:
        cached = await redis.get(STATS_KEY)
        if cached is not None:
            return json.loads(cached), HIT
    except RedisError as exc:
        logger.warning("stats cache read failed, bypassing cache: %s", exc)
        return await loader(), BYPASS

    stats = await loader()
    try:
        await redis.set(STATS_KEY, json.dumps(stats), ex=STATS_TTL_SECONDS)
    except RedisError as exc:
        logger.warning("stats cache write failed: %s", exc)
    return stats, MISS


async def invalidate_stats(redis: Redis) -> None:
    """Drop the cached stats after a complaint is created or its status changes.

    Called only once the database write has committed, so a Redis failure here
    must not fail the request: the entry then simply expires via its TTL.
    """
    try:
        await redis.delete(STATS_KEY)
    except RedisError as exc:
        logger.warning("stats cache invalidation failed, entry expires via TTL: %s", exc)
