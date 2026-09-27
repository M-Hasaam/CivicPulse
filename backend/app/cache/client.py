from redis.asyncio import Redis

from app.config import settings

# One shared client per process; redis-py manages its own connection pool.
# decode_responses=True so cached JSON and counters come back as str, not bytes.
redis_client: Redis = Redis.from_url(settings.REDIS_URL, decode_responses=True)


async def get_redis() -> Redis:
    """FastAPI dependency returning the shared client."""
    return redis_client


async def ping_redis() -> None:
    """Raise if Redis is unreachable. Used by the readiness probe."""
    await redis_client.ping()
