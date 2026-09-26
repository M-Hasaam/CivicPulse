import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, Enum, Index, Integer, String, func, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from app.domain import Category, Priority, Status


class Base(DeclarativeBase):
    pass


class ComplaintModel(Base):
    __tablename__ = "complaints"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    text: Mapped[str] = mapped_column(String(2000), nullable=False)
    location: Mapped[str] = mapped_column(String(200), nullable=False)
    reporter_contact: Mapped[str | None] = mapped_column(String(100), nullable=True)

    category: Mapped[Category] = mapped_column(Enum(Category, name="category_enum"), nullable=False)
    priority: Mapped[Priority] = mapped_column(Enum(Priority, name="priority_enum"), nullable=False)
    status: Mapped[Status] = mapped_column(
        Enum(Status, name="status_enum"), nullable=False, server_default=Status.open.value
    )

    ai_summary: Mapped[str | None] = mapped_column(String(140), nullable=True)
    triaged_by: Mapped[str] = mapped_column(String(32), nullable=False)
    triage_latency_ms: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    __table_args__ = (
        CheckConstraint("char_length(text) BETWEEN 10 AND 2000", name="ck_complaints_text_len"),
        CheckConstraint(
            "char_length(location) BETWEEN 3 AND 200", name="ck_complaints_location_len"
        ),
        # Dashboard filter: WHERE status = ? AND priority = ?
        Index("ix_complaints_status_priority", "status", "priority"),
        # Dashboard default ordering: ORDER BY created_at DESC LIMIT/OFFSET
        Index("ix_complaints_created_at", "created_at"),
    )
