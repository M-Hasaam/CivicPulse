import logging
import time
from typing import Annotated

from fastapi import Depends, HTTPException, Request, status
from redis.asyncio import Redis
from redis.exceptions import RedisError

from app.cache.client import get_redis
from app.config import settings

logger = logging.getLogger(__name__)


def client_identifier(request: Request) -> str:
    """Who to rate-limit: the real client, not the reverse proxy in front of us.

    Behind nginx/ingress every request arrives from the proxy's IP, so we use the
    first X-Forwarded-For entry. That header is only trustworthy when a proxy we
    control sets it; a client hitting the backend directly could spoof it.
    """
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


async def check_rate_limit(redis: Redis, identifier: str, limit: int, window_seconds: int) -> bool:
    """Fixed-window counter: True if this request is within the limit.

    One key per (client, window). INCR and EXPIRE NX run in a single pipeline, so
    the counter can never be left without a TTL. Fails open if Redis is down:
    rejecting citizens' complaints because the cache is unavailable would be worse
    than briefly not rate-limiting.
    """
    window = int(time.time() // window_seconds)
    key = f"ratelimit:{identifier}:{window}"
    try:
        async with redis.pipeline(transaction=True) as pipe:
            pipe.incr(key)
            pipe.expire(key, window_seconds, nx=True)
            count, _ = await pipe.execute()
    except RedisError as exc:
        logger.warning("rate limiter unavailable, allowing request: %s", exc)
        return True
    return int(count) <= limit


async def enforce_rate_limit(
    request: Request, redis: Annotated[Redis, Depends(get_redis)]
) -> None:
    """FastAPI dependency: raise 429 once a client exceeds the configured limit."""
    allowed = await check_rate_limit(
        redis,
        client_identifier(request),
        settings.RATE_LIMIT_MAX_REQUESTS,
        settings.RATE_LIMIT_WINDOW_SECONDS,
    )
    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many requests. Please try again later.",
        )
