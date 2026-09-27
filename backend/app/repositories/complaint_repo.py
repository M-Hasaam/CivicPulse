import uuid
from typing import Any

from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain import Category, Priority, Status
from app.repositories.models import ComplaintModel


class ComplaintRepository:
    """All complaint SQL lives here and nowhere else."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, data: dict[str, Any]) -> ComplaintModel:
        complaint = ComplaintModel(**data)
        self.session.add(complaint)
        await self.session.commit()
        await self.session.refresh(complaint)
        return complaint

    async def get_by_id(self, complaint_id: uuid.UUID) -> ComplaintModel | None:
        return await self.session.get(ComplaintModel, complaint_id)

    async def get_by_id_for_update(self, complaint_id: uuid.UUID) -> ComplaintModel | None:
        """Like get_by_id, but locks the row (SELECT ... FOR UPDATE) until the
        surrounding transaction commits or rolls back.

        Without this, two concurrent status changes on the same complaint can both
        read the old status, both pass the state-machine check against it, and both
        commit - a classic lost update where the loser's write silently disappears
        and its 200 response lies about the final state. With the lock, the second
        request's read blocks until the first commits, then it re-reads the row and
        validates against the *current* status, so at most one of two conflicting
        transitions can ever succeed.
        """
        return await self.session.scalar(self._for_update_statement(complaint_id))

    @staticmethod
    def _for_update_statement(complaint_id: uuid.UUID) -> Select[ComplaintModel]:
        return select(ComplaintModel).where(ComplaintModel.id == complaint_id).with_for_update()

    async def get_by_text(self, text: str) -> ComplaintModel | None:
        result = await self.session.execute(
            select(ComplaintModel).where(ComplaintModel.text == text).limit(1)
        )
        return result.scalar_one_or_none()

    async def list_complaints(
        self,
        category: Category | None = None,
        priority: Priority | None = None,
        status: Status | None = None,
        page: int = 1,
        page_size: int = 10,
    ) -> tuple[list[ComplaintModel], int]:
        def filtered(stmt: Select[Any]) -> Select[Any]:
            if category:
                stmt = stmt.where(ComplaintModel.category == category)
            if priority:
                stmt = stmt.where(ComplaintModel.priority == priority)
            if status:
                stmt = stmt.where(ComplaintModel.status == status)
            return stmt

        total = await self.session.scalar(filtered(select(func.count(ComplaintModel.id)))) or 0

        page_stmt = (
            filtered(select(ComplaintModel))
            # id breaks ties: rows inserted in one transaction share created_at = now()
            .order_by(ComplaintModel.created_at.desc(), ComplaintModel.id.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        items = list((await self.session.scalars(page_stmt)).all())
        return items, total

    async def update_status(self, complaint: ComplaintModel, new_status: Status) -> ComplaintModel:
        complaint.status = new_status
        await self.session.commit()
        await self.session.refresh(complaint)
        return complaint

    async def _count_by(self, column: Any) -> dict[str, int]:
        result = await self.session.execute(
            select(column, func.count(ComplaintModel.id)).group_by(column)
        )
        return {str(key): count for key, count in result.all()}

    async def get_aggregates(self) -> dict[str, Any]:
        total = await self.session.scalar(select(func.count(ComplaintModel.id))) or 0
        avg_latency = await self.session.scalar(select(func.avg(ComplaintModel.triage_latency_ms)))
        return {
            "total_complaints": total,
            "by_category": await self._count_by(ComplaintModel.category),
            "by_priority": await self._count_by(ComplaintModel.priority),
            "by_status": await self._count_by(ComplaintModel.status),
            "avg_triage_latency_ms": round(float(avg_latency or 0), 2),
        }
