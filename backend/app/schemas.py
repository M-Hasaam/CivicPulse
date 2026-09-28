"""HTTP request/response shapes. The same Pydantic machinery validates model
output in the providers - one mental model for both."""

import uuid
from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

from app.domain import Category, Priority, Status

ComplaintText = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=10, max_length=2000)
]
Location = Annotated[str, StringConstraints(strip_whitespace=True, min_length=3, max_length=200)]
Contact = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)]


class ComplaintCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    text: ComplaintText
    location: Location
    reporter_contact: Contact | None = None


class StatusUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: Status


class ComplaintOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    text: str
    location: str
    reporter_contact: str | None
    category: Category
    priority: Priority
    status: Status
    ai_summary: str | None
    triaged_by: str
    triage_latency_ms: int
    created_at: datetime
    updated_at: datetime


class ComplaintPage(BaseModel):
    items: list[ComplaintOut]
    total: int
    page: int
    page_size: int


class StatsOut(BaseModel):
    total_complaints: int
    by_category: dict[str, int]
    by_priority: dict[str, int]
    by_status: dict[str, int]
    avg_triage_latency_ms: float


class TriageOutcomeOut(BaseModel):
    provider: str
    latency_ms: int
    fallback: bool
    cached: bool
    at: datetime


class TriageCacheStats(BaseModel):
    hits: int
    misses: int
    hit_rate: float | None = Field(description="hits / lookups; null before the first lookup")


class ProviderMeta(BaseModel):
    active_provider: str
    fallback_provider: str
    recent_outcomes: list[TriageOutcomeOut]
    triage_cache: TriageCacheStats


class ErrorOut(BaseModel):
    detail: str


class FieldError(BaseModel):
    field: str
    in_: str = Field(alias="in", description="body, query or path")
    message: str


class ValidationErrorOut(BaseModel):
    detail: str
    errors: list[FieldError]


class TransitionErrorOut(BaseModel):
    """409 body for PATCH .../status: the fields _invalid_transition actually
    returns, so a generated client can type and discover them instead of only
    the bare `detail` string that ErrorOut promises."""

    detail: str
    current_status: Status
    attempted_status: Status
