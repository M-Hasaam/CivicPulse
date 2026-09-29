import json
import logging
import uuid
from typing import cast

import pytest
from redis.asyncio import Redis

from app.cache import stats_cache
from app.domain import Category, Priority, Status
from app.providers.triage.rules import RuleBasedTriage
from app.providers.triage.simulated import SimulatedTriage
from app.repositories.complaint_repo import ComplaintRepository
from app.services.complaint_service import ComplaintNotFoundError, ComplaintService
from app.services.state_machine import InvalidTransitionError
from app.services.triage_service import TriageOrchestrator
from tests.fakes import FakeComplaintRepository

pytestmark = pytest.mark.anyio

TEXT = "Transformer sparking near the school gate since morning"


def make_service(
    redis: Redis, failure: str = "none"
) -> tuple[ComplaintService, FakeComplaintRepository]:
    repo = FakeComplaintRepository()
    provider = SimulatedTriage(failure=failure)  # type: ignore[arg-type]
    orchestrator = TriageOrchestrator([provider, RuleBasedTriage()])
    service = ComplaintService(cast(ComplaintRepository, repo), redis, orchestrator)
    return service, repo


async def test_create_persists_the_triage_result(redis: Redis) -> None:
    service, repo = make_service(redis)
    complaint = await service.create(TEXT, "F-6/1", None)
    assert complaint.id in repo.rows
    assert (complaint.category, complaint.priority) == (Category.electricity, Priority.high)
    assert complaint.triaged_by == "simulated" and complaint.ai_summary
    assert complaint.status is Status.open


async def test_fallback_logs_one_warning_with_id_provider_and_error(
    redis: Redis, caplog: pytest.LogCaptureFixture
) -> None:
    service, _ = make_service(redis, failure="raise")
    with caplog.at_level(logging.WARNING, logger="app.services.complaint_service"):
        complaint = await service.create(TEXT, "F-6/1", None)
    assert complaint.triaged_by == "rules:fallback"
    warnings = [r for r in caplog.records if r.name == "app.services.complaint_service"]
    assert len(warnings) == 1
    record = warnings[0]
    assert record.complaint_id == str(complaint.id)  # type: ignore[attr-defined]
    assert record.provider == "simulated"  # type: ignore[attr-defined]
    assert record.error_class == "TriageUnavailableError"  # type: ignore[attr-defined]


async def test_writes_invalidate_the_stats_cache(redis: Redis) -> None:
    service, _ = make_service(redis)
    first = await service.create(TEXT, "F-6/1", None)

    _, state = await service.stats()
    assert state == stats_cache.MISS
    _, state = await service.stats()
    assert state == stats_cache.HIT  # served from cache, not recomputed

    await service.create("Pothole crater on the main double road", "Kashmir Hwy", None)
    stats, state = await service.stats()
    assert state == stats_cache.MISS  # the write invalidated the cache, not just expiry
    assert stats["total_complaints"] == 2  # new complaint shows immediately

    await service.stats()  # repopulate the cache
    await service.change_status(first.id, Status.in_progress)
    _, state = await service.stats()
    assert state == stats_cache.MISS  # a status change invalidates it too


async def test_stats_are_a_hit_on_the_second_read(redis: Redis) -> None:
    service, _ = make_service(redis)
    await service.create(TEXT, "F-6/1", None)
    first, first_state = await service.stats()
    second, second_state = await service.stats()
    assert (first_state, second_state) == (stats_cache.MISS, stats_cache.HIT)
    assert first == second and first["total_complaints"] == 1


async def test_status_changes_follow_the_state_machine(redis: Redis) -> None:
    service, _ = make_service(redis)
    complaint = await service.create(TEXT, "F-6/1", None)
    with pytest.raises(InvalidTransitionError):
        await service.change_status(complaint.id, Status.resolved)
    await service.change_status(complaint.id, Status.in_progress)
    updated = await service.change_status(complaint.id, Status.resolved)
    assert updated.status is Status.resolved


async def test_unknown_complaint_raises_not_found(redis: Redis) -> None:
    service, _ = make_service(redis)
    with pytest.raises(ComplaintNotFoundError):
        await service.get(uuid.uuid4())
    with pytest.raises(ComplaintNotFoundError):
        await service.change_status(uuid.uuid4(), Status.in_progress)


async def test_provider_meta_reports_outcomes_and_hit_rate(redis: Redis) -> None:
    service, _ = make_service(redis)
    await service.create(TEXT, "F-6/1", None)
    await service.create(TEXT, "F-6/1", None)  # duplicate report -> cache hit
    meta = await service.provider_meta()
    assert meta["active_provider"] == "simulated"
    assert [o["cached"] for o in meta["recent_outcomes"]] == [True, False]
    assert meta["triage_cache"] == {"hits": 1, "misses": 1, "hit_rate": 0.5}
    json.dumps(meta)  # serialisable as-is
