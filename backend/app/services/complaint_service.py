"""Business rules for complaints. Routes call this; this calls the repository,
the triage orchestrator and the caches. No HTTP and no SQL here."""

import logging
import uuid
from typing import Any

from redis.asyncio import Redis

from app.cache import stats_cache, triage_log
from app.domain import Category, Priority, Status
from app.repositories.complaint_repo import ComplaintRepository
from app.repositories.models import ComplaintModel
from app.services.state_machine import ensure_transition
from app.services.triage_service import TriageOrchestrator

logger = logging.getLogger(__name__)


class ComplaintNotFoundError(Exception):
    def __init__(self, complaint_id: uuid.UUID) -> None:
        super().__init__(f"Complaint {complaint_id} not found")


class ComplaintService:
    def __init__(
        self, repo: ComplaintRepository, redis: Redis, triage: TriageOrchestrator
    ) -> None:
        self.repo = repo
        self.redis = redis
        self.triage = triage

    async def create(
        self, text: str, location: str, reporter_contact: str | None
    ) -> ComplaintModel:
        outcome = await self.triage.triage(text, location, self.redis)
        complaint = await self.repo.create(
            {
                "text": text,
                "location": location,
                "reporter_contact": reporter_contact,
                "category": outcome.result.category,
                "priority": outcome.result.priority,
                "ai_summary": outcome.result.summary,
                "triaged_by": outcome.triaged_by,
                "triage_latency_ms": outcome.latency_ms,
            }
        )
        if outcome.fallback:
            logger.warning(
                "triage fell back to rules",
                extra={
                    "complaint_id": str(complaint.id),
                    "provider": self.triage.provider.name,
                    "error_class": outcome.error_class,
                },
            )
        # Only after the write has committed; a Redis failure here is logged, not raised
        await stats_cache.invalidate_stats(self.redis)
        return complaint

    @staticmethod
    def _require(complaint: ComplaintModel | None, complaint_id: uuid.UUID) -> ComplaintModel:
        if complaint is None:
            raise ComplaintNotFoundError(complaint_id)
        return complaint

    async def get(self, complaint_id: uuid.UUID) -> ComplaintModel:
        complaint = await self.repo.get_by_id(complaint_id)
        return self._require(complaint, complaint_id)

    async def list(
        self,
        category: Category | None,
        priority: Priority | None,
        status: Status | None,
        page: int,
        page_size: int,
    ) -> tuple[list[ComplaintModel], int]:
        return await self.repo.list_complaints(category, priority, status, page, page_size)

    async def change_status(self, complaint_id: uuid.UUID, target: Status) -> ComplaintModel:
        # Locks the row until update_status commits, so a concurrent change to the
        # same complaint waits, then validates against the status this one left
        # behind - see get_by_id_for_update's docstring.
        complaint = await self.repo.get_by_id_for_update(complaint_id)
        complaint = self._require(complaint, complaint_id)
        ensure_transition(complaint.status, target)  # raises InvalidTransitionError -> 409
        updated = await self.repo.update_status(complaint, target)
        await stats_cache.invalidate_stats(self.redis)
        return updated

    async def stats(self) -> tuple[dict[str, Any], str]:
        """Aggregates plus the X-Cache value (HIT, MISS or BYPASS)."""
        return await stats_cache.get_stats(self.redis, self.repo.get_aggregates)

    async def provider_meta(self) -> dict[str, Any]:
        hits, misses = await triage_log.cache_counts(self.redis)
        lookups = hits + misses
        return {
            "active_provider": self.triage.provider.name,
            "fallback_provider": "rules",
            "recent_outcomes": await triage_log.recent_outcomes(self.redis),
            "triage_cache": {
                "hits": hits,
                "misses": misses,
                "hit_rate": round(hits / lookups, 3) if lookups else None,
            },
        }
