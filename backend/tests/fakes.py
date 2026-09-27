"""In-memory stand-ins shared by service and route tests (no database needed)."""

import uuid
from collections import Counter
from datetime import UTC, datetime, timedelta
from typing import Any

from app.domain import Category, Priority, Status
from app.repositories.models import ComplaintModel


class FakeComplaintRepository:
    """Implements the ComplaintRepository methods the service uses, in a dict."""

    def __init__(self) -> None:
        self.rows: dict[uuid.UUID, ComplaintModel] = {}
        self._clock = datetime(2026, 9, 27, tzinfo=UTC)

    async def create(self, data: dict[str, Any]) -> ComplaintModel:
        self._clock += timedelta(seconds=1)
        complaint = ComplaintModel(
            id=uuid.uuid4(),
            status=Status.open,
            created_at=self._clock,
            updated_at=self._clock,
            **data,
        )
        self.rows[complaint.id] = complaint
        return complaint

    async def get_by_id(self, complaint_id: uuid.UUID) -> ComplaintModel | None:
        return self.rows.get(complaint_id)

    async def list_complaints(
        self,
        category: Category | None = None,
        priority: Priority | None = None,
        status: Status | None = None,
        page: int = 1,
        page_size: int = 10,
    ) -> tuple[list[ComplaintModel], int]:
        matches = [
            c
            for c in sorted(self.rows.values(), key=lambda c: c.created_at, reverse=True)
            if (category is None or c.category == category)
            and (priority is None or c.priority == priority)
            and (status is None or c.status == status)
        ]
        start = (page - 1) * page_size
        return matches[start : start + page_size], len(matches)

    async def update_status(self, complaint: ComplaintModel, new_status: Status) -> ComplaintModel:
        complaint.status = new_status
        self._clock += timedelta(seconds=1)
        complaint.updated_at = self._clock
        return complaint

    async def get_aggregates(self) -> dict[str, Any]:
        rows = list(self.rows.values())
        latencies = [c.triage_latency_ms for c in rows]
        return {
            "total_complaints": len(rows),
            "by_category": dict(Counter(c.category.value for c in rows)),
            "by_priority": dict(Counter(c.priority.value for c in rows)),
            "by_status": dict(Counter(c.status.value for c in rows)),
            "avg_triage_latency_ms": round(sum(latencies) / len(latencies), 2) if rows else 0.0,
        }
