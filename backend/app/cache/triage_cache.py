import hashlib
import json
import logging
from typing import Any

from redis.asyncio import Redis
from redis.exceptions import RedisError

logger = logging.getLogger(__name__)

TRIAGE_TTL_SECONDS = 24 * 60 * 60

# Bump when the stored result shape changes so old entries are simply never read.
_KEY_PREFIX = "triage:v1:"


def triage_key(text: str) -> str:
    """Cache key from the complaint content: case and whitespace differences don't matter."""
    normalized = " ".join(text.lower().split())
    return _KEY_PREFIX + hashlib.sha256(normalized.encode("utf-8")).hexdigest()


async def get_cached_triage(redis: Redis, text: str) -> dict[str, Any] | None:
    """Return a previously stored triage result for this text, or None on a miss.

    Any Redis error, or a stored value that turns out not to be a JSON object
    (corrupted, truncated, or written by a since-changed version of this cache),
    counts as a miss: triage then just runs as if uncached, rather than a 500.
    """
    try:
        cached = await redis.get(triage_key(text))
    except RedisError as exc:
        logger.warning("triage cache read failed, treating as miss: %s", exc)
        return None
    if cached is None:
        return None
    try:
        entry = json.loads(cached)
    except json.JSONDecodeError:
        logger.warning("triage cache entry is not valid JSON, treating as miss")
        return None
    if not isinstance(entry, dict):
        logger.warning("triage cache entry is not a JSON object, treating as miss")
        return None
    return entry


async def cache_triage(redis: Redis, text: str, result: dict[str, Any]) -> None:
    """Store a triage result for 24h.

    Callers must only store results from the primary (LLM) provider, never the
    rule-based fallback: otherwise a brief LLM outage would pin fallback answers
    in the cache for a full day after the LLM recovers.
    """
    try:
        await redis.set(triage_key(text), json.dumps(result), ex=TRIAGE_TTL_SECONDS)
    except RedisError as exc:
        logger.warning("triage cache write failed: %s", exc)
