import os
from collections.abc import AsyncIterator

import fakeredis.aioredis
import pytest
from redis.asyncio import Redis

# Settings require DATABASE_URL; tests never connect, so any well-formed URL works.
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://test:test@db.invalid:5432/test")


@pytest.fixture
def anyio_backend() -> str:
    # async tests run on asyncio only (anyio would otherwise also try trio)
    return "asyncio"


@pytest.fixture
async def redis() -> AsyncIterator[Redis]:
    """In-memory Redis: cache tests need no server, locally or in CI."""
    client = fakeredis.aioredis.FakeRedis(decode_responses=True)
    yield client
    await client.aclose()
