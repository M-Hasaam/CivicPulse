import logging
import math
import time
from typing import Annotated

from fastapi import Depends, HTTPException, Request, status
from redis.asyncio import Redis
from redis.exceptions import RedisError

from app.cache.client import get_redis
from app.config import settings

logger = logging.getLogger(__name__)


def client_identifier(request: Request) -> str:
    """Who to rate-limit: the real client, without trusting what the client says about itself.

    Each proxy we run appends the address it saw to X-Forwarded-For, so with N trusted
    proxies the Nth entry from the END is the real client. Everything before it was
    supplied by the client and is ignored: taking the first entry would let anyone
    dodge the limit by sending a different fake address on every request.

    Falls back to the socket address when the header is absent or shorter than the
    number of trusted proxies (a request that did not come through our proxies).
    """
    hops = settings.TRUSTED_PROXY_HOPS
    if hops > 0:
        entries = [e.strip() for e in request.headers.get("x-forwarded-for", "").split(",")]
        entries = [e for e in entries if e]
        if len(entries) >= hops:
            return entries[-hops]
    return request.client.host if request.client else "unknown"


def retry_after_seconds(window_seconds: int) -> int:
    """Whole seconds until the current fixed window ends (never less than 1)."""
    return max(1, math.ceil(window_seconds - time.time() % window_seconds))


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
            headers={"Retry-After": str(retry_after_seconds(settings.RATE_LIMIT_WINDOW_SECONDS))},
        )
