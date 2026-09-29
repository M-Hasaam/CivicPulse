import pytest
from redis.asyncio import Redis

from app.cache import triage_log
from app.domain import Category, Priority
from app.providers.triage.base import TriageResult, TriageUnavailableError
from app.providers.triage.rules import RuleBasedTriage
from app.providers.triage.simulated import SimulatedTriage
from app.services.triage_service import FALLBACK_NAME, TriageOrchestrator

pytestmark = pytest.mark.anyio

TEXT = "Burst water main flooding Street 12 since fajr"


class CountingProvider:
    """A provider that records how often it was actually called."""

    def __init__(self, name: str = "llm:test", error: Exception | None = None) -> None:
        self.name = name
        self.error = error
        self.calls = 0

    async def triage(self, text: str, location: str) -> TriageResult:
        self.calls += 1
        if self.error:
            raise self.error
        return TriageResult(
            category=Category.water, priority=Priority.high, summary="Burst main", confidence=0.9
        )


async def test_primary_provider_result_is_used_and_recorded(redis: Redis) -> None:
    outcome = await TriageOrchestrator([CountingProvider(), RuleBasedTriage()]).triage(
        TEXT, "G-10", redis
    )
    assert (outcome.triaged_by, outcome.fallback, outcome.cached) == ("llm:test", False, False)
    assert outcome.latency_ms >= 0
    recent = await triage_log.recent_outcomes(redis)
    assert recent[0]["provider"] == "llm:test" and recent[0]["fallback"] is False


async def test_any_provider_failure_falls_back_to_rules(redis: Redis) -> None:
    provider = CountingProvider(error=TriageUnavailableError("429"))
    outcome = await TriageOrchestrator([provider, RuleBasedTriage()]).triage(TEXT, "G-10", redis)
    assert outcome.triaged_by == FALLBACK_NAME == "rules:fallback"
    assert outcome.fallback and outcome.error_class == "TriageUnavailableError"
    assert outcome.result.category is Category.water  # decided by the rules, not lost


async def test_even_an_unexpected_bug_in_a_provider_falls_back(redis: Redis) -> None:
    provider = CountingProvider(error=KeyError("choices"))
    outcome = await TriageOrchestrator([provider, RuleBasedTriage()]).triage(TEXT, "G-10", redis)
    assert outcome.triaged_by == FALLBACK_NAME and outcome.error_class == "KeyError"


async def test_malformed_model_output_falls_back(redis: Redis) -> None:
    outcome = await TriageOrchestrator(
        [SimulatedTriage(failure="malformed"), RuleBasedTriage()]
    ).triage(TEXT, "G-10", redis)
    assert outcome.fallback and outcome.error_class == "InvalidTriageOutputError"


async def test_duplicate_complaint_costs_one_inference(redis: Redis) -> None:
    provider = CountingProvider()
    orchestrator = TriageOrchestrator([provider, RuleBasedTriage()])
    first = await orchestrator.triage(TEXT, "G-10", redis)
    duplicate = "  burst WATER main flooding street 12 since fajr "  # a neighbour's report
    second = await orchestrator.triage(duplicate, "x", redis)
    assert provider.calls == 1
    assert (first.cached, second.cached) == (False, True)
    assert second.triaged_by == "llm:test" and second.result == first.result
    assert await triage_log.cache_counts(redis) == (1, 1)  # one hit, one miss


async def test_fallback_results_are_never_cached(redis: Redis) -> None:
    failing = CountingProvider(error=TriageUnavailableError("down"))
    await TriageOrchestrator([failing, RuleBasedTriage()]).triage(TEXT, "G-10", redis)

    recovered = CountingProvider()
    outcome = await TriageOrchestrator([recovered, RuleBasedTriage()]).triage(TEXT, "G-10", redis)
    assert recovered.calls == 1 and not outcome.cached and not outcome.fallback


async def test_cache_from_a_different_provider_is_ignored(redis: Redis) -> None:
    await TriageOrchestrator([CountingProvider(name="simulated"), RuleBasedTriage()]).triage(
        TEXT, "G-10", redis
    )
    llm = CountingProvider(name="llm:groq")
    outcome = await TriageOrchestrator([llm, RuleBasedTriage()]).triage(TEXT, "G-10", redis)
    assert llm.calls == 1 and outcome.triaged_by == "llm:groq" and not outcome.cached


async def test_only_the_last_20_outcomes_are_kept(redis: Redis) -> None:
    orchestrator = TriageOrchestrator([CountingProvider(), RuleBasedTriage()])
    for i in range(25):
        await orchestrator.triage(f"{TEXT} report number {i}", "G-10", redis)
    assert len(await triage_log.recent_outcomes(redis)) == 20
