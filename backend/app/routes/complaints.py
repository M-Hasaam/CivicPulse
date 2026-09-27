"""HTTP only: parse, validate, call the service, serialise, choose status codes."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status

from app.cache.rate_limiter import enforce_rate_limit
from app.dependencies import Service
from app.domain import Category, Priority, Status
from app.schemas import (
    ComplaintCreate,
    ComplaintOut,
    ComplaintPage,
    ErrorOut,
    StatusUpdate,
    TransitionErrorOut,
    ValidationErrorOut,
)

router = APIRouter(
    prefix="/api/complaints",
    tags=["complaints"],
    responses={400: {"model": ValidationErrorOut, "description": "Validation failed"}},
)


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(enforce_rate_limit)],
    responses={429: {"model": ErrorOut}},
)
async def create_complaint(body: ComplaintCreate, service: Service) -> ComplaintOut:
    complaint = await service.create(body.text, body.location, body.reporter_contact)
    return ComplaintOut.model_validate(complaint)


@router.get("/{complaint_id}", responses={404: {"model": ErrorOut}})
async def get_complaint(complaint_id: uuid.UUID, service: Service) -> ComplaintOut:
    return ComplaintOut.model_validate(await service.get(complaint_id))


@router.get("")
async def list_complaints(
    service: Service,
    category: Category | None = None,
    priority: Priority | None = None,
    status_: Annotated[Status | None, Query(alias="status")] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> ComplaintPage:
    items, total = await service.list(category, priority, status_, page, page_size)
    return ComplaintPage(
        items=[ComplaintOut.model_validate(c) for c in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.patch(
    "/{complaint_id}/status",
    responses={404: {"model": ErrorOut}, 409: {"model": TransitionErrorOut}},
)
async def change_status(
    complaint_id: uuid.UUID, body: StatusUpdate, service: Service
) -> ComplaintOut:
    return ComplaintOut.model_validate(await service.change_status(complaint_id, body.status))
