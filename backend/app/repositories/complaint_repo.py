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
            .order_by(ComplaintModel.created_at.desc())
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
