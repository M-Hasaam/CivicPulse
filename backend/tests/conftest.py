import os
from collections.abc import AsyncIterator

import fakeredis.aioredis
import pytest
from redis.asyncio import Redis

# Settings require DATABASE_URL; tests never connect, so any well-formed URL works.
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://test:test@db.invalid:5432/test")
# Real environment variables beat the developer's .env: tests must never reach a live
# LLM (non-deterministic, rate-limited, and it would spend the key's quota).
os.environ["TRIAGE_PROVIDER"] = "simulated"


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
