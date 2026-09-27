"""The process-wide Redis client.

It is created inside the application lifespan, i.e. on the event loop that will
use it, and closed on shutdown. A client built at import time binds its pooled
connections to whichever loop touches it first, which breaks as soon as a
second loop appears (and never gets closed on SIGTERM).
"""

from redis.asyncio import Redis

from app.config import settings

_client: Redis | None = None


def connect_redis() -> Redis:
    global _client
    # decode_responses=True so cached JSON and counters come back as str, not bytes.
    _client = Redis.from_url(settings.REDIS_URL, decode_responses=True)
    return _client


async def close_redis() -> None:
    global _client
    if _client is not None:
        await _client.aclose()
        _client = None


def redis_client() -> Redis:
    if _client is None:
        raise RuntimeError("Redis client is not initialised: is the app lifespan running?")
    return _client


async def get_redis() -> Redis:
    """FastAPI dependency returning the shared client."""
    return redis_client()


async def ping_redis() -> None:
    """Raise if Redis is unreachable. Used by the readiness probe."""
    await redis_client().ping()
