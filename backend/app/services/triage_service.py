"""Triage orchestration: cache, primary provider, rule-based fallback.

The rest of the system calls TriageOrchestrator.triage and never learns which
provider answered or whether it failed - only what triaged_by to record.
"""

import logging
import time
from dataclasses import dataclass
from datetime import UTC, datetime

from pydantic import ValidationError
from redis.asyncio import Redis

from app.cache import triage_log
from app.cache.triage_cache import cache_triage, get_cached_triage
from app.metrics import TRIAGE_CACHE, TRIAGE_FALLBACKS, TRIAGE_LATENCY
from app.providers.triage.base import TriageProvider, TriageResult
from app.providers.triage.rules import RuleBasedTriage

logger = logging.getLogger(__name__)

FALLBACK_NAME = "rules:fallback"


@dataclass(frozen=True)
class TriageOutcome:
    result: TriageResult
    triaged_by: str
    latency_ms: int
    fallback: bool
    cached: bool
    error_class: str | None = None


class TriageOrchestrator:
    def __init__(self, provider: TriageProvider, fallback: TriageProvider | None = None) -> None:
        self.provider = provider
        self.fallback = fallback or RuleBasedTriage()

    async def triage(self, text: str, location: str, redis: Redis) -> TriageOutcome:
        started = time.perf_counter()

        outcome = await self._from_cache(text, redis, started)
        if outcome is None:
            outcome = await self._from_provider(text, location, started)
            if not outcome.fallback:
                # Never cache a fallback answer: a short LLM outage would otherwise
                # pin rule-based results for 24h after the LLM recovers.
                await cache_triage(
                    redis,
                    text,
                    {"triaged_by": outcome.triaged_by, "result": outcome.result.model_dump()},
                )

        TRIAGE_LATENCY.labels(provider=outcome.triaged_by).observe(outcome.latency_ms / 1000)
        await triage_log.record_outcome(
            redis,
            {
                "provider": outcome.triaged_by,
                "latency_ms": outcome.latency_ms,
                "fallback": outcome.fallback,
                "cached": outcome.cached,
                "at": datetime.now(UTC).isoformat(),
            },
        )
        return outcome

    async def _from_cache(self, text: str, redis: Redis, started: float) -> TriageOutcome | None:
        entry = await get_cached_triage(redis, text)
        hit = False
        outcome = None
        # Only reuse an answer from the provider that is configured now
        if entry is not None and entry.get("triaged_by") == self.provider.name:
            try:
                outcome = TriageOutcome(
                    result=TriageResult.model_validate(entry["result"]),
                    triaged_by=self.provider.name,
                    latency_ms=_elapsed_ms(started),
                    fallback=False,
                    cached=True,
                )
                hit = True
            except (KeyError, ValidationError):
                logger.warning("ignoring malformed triage cache entry")
        TRIAGE_CACHE.labels(result="hit" if hit else "miss").inc()
        await triage_log.count_cache_lookup(redis, hit)
        return outcome

    async def _from_provider(self, text: str, location: str, started: float) -> TriageOutcome:
        try:
            result = await self.provider.triage(text, location)
        except Exception as exc:  # any provider failure - known or not - must not reach the user
            error_class = type(exc).__name__
            TRIAGE_FALLBACKS.labels(provider=self.provider.name, error=error_class).inc()
            result = await self.fallback.triage(text, location)
            return TriageOutcome(
                result=result,
                triaged_by=FALLBACK_NAME,
                latency_ms=_elapsed_ms(started),
                fallback=True,
                cached=False,
                error_class=error_class,
            )
        return TriageOutcome(
            result=result,
            triaged_by=self.provider.name,
            latency_ms=_elapsed_ms(started),
            fallback=False,
            cached=False,
        )


def _elapsed_ms(started: float) -> int:
    return round((time.perf_counter() - started) * 1000)
