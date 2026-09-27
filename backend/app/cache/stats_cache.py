import json
import logging
from collections.abc import Awaitable, Callable
from typing import Any

from redis.asyncio import Redis
from redis.exceptions import RedisError

logger = logging.getLogger(__name__)

STATS_KEY_PREFIX = "cache:stats"
STATS_VERSION_KEY = "cache:stats:version"
STATS_TTL_SECONDS = 30

# Values for the X-Cache response header.
HIT = "HIT"
MISS = "MISS"
BYPASS = "BYPASS"  # Redis unavailable: answered straight from the database


async def current_stats_key(redis: Redis) -> str:
    """The cache key for the current generation.

    invalidate_stats bumps the generation counter rather than deleting the entry
    in place, so a read that is already mid-flight when an invalidation happens
    (it queried the database, but has not written its result to cache yet) still
    lands under the OLD key once it does write - a key this function will never
    return again, so no future reader can ever observe that stale write. Deleting
    the key in place cannot make that guarantee: a write landing right after the
    delete brings the stale data straight back for up to STATS_TTL_SECONDS.
    """
    version = await redis.get(STATS_VERSION_KEY)
    if not version:
        return f"{STATS_KEY_PREFIX}:0"
    try:
        return f"{STATS_KEY_PREFIX}:{int(version)}"
    except (TypeError, ValueError):
        logger.warning("stats cache version %r is not an integer, treating as gen 0", version)
        return f"{STATS_KEY_PREFIX}:0"


async def get_stats(
    redis: Redis, loader: Callable[[], Awaitable[dict[str, Any]]]
) -> tuple[dict[str, Any], str]:
    """Read-through cache: return (stats, X-Cache value).

    A cache outage must never take the endpoint down, so any Redis error falls
    back to computing the stats directly.
    """
    try:
        key = await current_stats_key(redis)
        cached = await redis.get(key)
    except RedisError as exc:
        logger.warning("stats cache read failed, bypassing cache: %s", exc)
        return await loader(), BYPASS
    if cached is not None:
        try:
            return json.loads(cached), HIT
        except json.JSONDecodeError:
            logger.warning("stats cache entry is not valid JSON, treating as miss")

    stats = await loader()
    try:
        # If invalidate_stats bumped the version while the database query above
        # was running, 'key' now names the previous generation: harmless, since
        # current_stats_key() will not hand that name to anyone else again.
        await redis.set(key, json.dumps(stats), ex=STATS_TTL_SECONDS)
    except RedisError as exc:
        logger.warning("stats cache write failed: %s", exc)
    return stats, MISS


async def invalidate_stats(redis: Redis) -> None:
    """Move every reader on to a fresh cache key after a complaint is created or
    its status changes. Called only once the database write has committed.

    A Redis failure here must not fail the request: the current generation's
    entry then simply expires via its TTL, same as before this fix.
    """
    try:
        await redis.incr(STATS_VERSION_KEY)
    except RedisError as exc:
        logger.warning("stats cache invalidation failed, entry expires via TTL: %s", exc)
