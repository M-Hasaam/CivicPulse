"""Triage orchestration: cache, then an ordered provider chain.

The rest of the system calls TriageOrchestrator.triage and never learns which
provider answered or whether it failed - only what triaged_by to record.
"""

import logging
import time
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime

from pydantic import ValidationError
from redis.asyncio import Redis

from app.cache import triage_log
from app.cache.triage_cache import cache_triage, get_cached_triage
from app.metrics import TRIAGE_CACHE, TRIAGE_FALLBACKS, TRIAGE_LATENCY
from app.providers.triage.base import TriageProvider, TriageResult

logger = logging.getLogger(__name__)

# Reported only when the chain's last, guaranteed-safe entry answers after every
# provider ahead of it has failed - never for a real provider answering as itself,
# even one that isn't first in the chain (e.g. Ollama answering because Groq is down
# is still a real AI answer, not a degraded one).
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
    def __init__(self, chain: Sequence[TriageProvider]) -> None:
        if not chain:
            raise ValueError("TriageOrchestrator needs at least one provider")
        self._chain = list(chain)
        # Kept for callers that log/inspect the primary provider (main.py's startup
        # log, complaint_service.py's fallback warning) - always the first hop, same
        # meaning as before this was a chain.
        self.provider = self._chain[0]
        self._provider_names = {p.name for p in self._chain}

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
        # Only reuse an answer from a provider that's actually in the chain right
        # now (any hop, not just the primary) - a cached FALLBACK_NAME entry never
        # exists in the first place, since fallback answers are never cached below.
        if entry is not None and entry.get("triaged_by") in self._provider_names:
            try:
                outcome = TriageOutcome(
                    result=TriageResult.model_validate(entry["result"]),
                    triaged_by=entry["triaged_by"],
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
        last_error_class: str | None = None
        last_index = len(self._chain) - 1
        for index, provider in enumerate(self._chain):
            try:
                result = await provider.triage(text, location)
            except Exception as exc:  # any failure, known or not - must not reach the user
                error_class = type(exc).__name__
                TRIAGE_FALLBACKS.labels(provider=provider.name, error=error_class).inc()
                if last_error_class is None:
                    last_error_class = error_class
                continue

            # Only the chain's terminal, guaranteed-safe entry counts as "fell back" -
            # a mid-chain provider (e.g. Ollama answering because Groq failed) is a
            # real answer in its own right: cacheable, and identified by its own name.
            is_last_resort = index == last_index and index > 0
            return TriageOutcome(
                result=result,
                triaged_by=FALLBACK_NAME if is_last_resort else provider.name,
                latency_ms=_elapsed_ms(started),
                fallback=is_last_resort,
                cached=False,
                error_class=last_error_class if index > 0 else None,
            )

        # Unreachable in practice: the chain always ends in RuleBasedTriage, which
        # cannot fail by its own design (no network, no state, no input it rejects).
        raise RuntimeError("every provider in the triage chain failed")


def _elapsed_ms(started: float) -> int:
    return round((time.perf_counter() - started) * 1000)
