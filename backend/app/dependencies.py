"""Wiring: how a request gets its service. Routes depend on ComplaintService
only; they never see a database session or a Redis client."""

from typing import Annotated

from fastapi import Depends, Request
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.cache.client import get_redis
from app.repositories.complaint_repo import ComplaintRepository
from app.repositories.database import get_db
from app.services.complaint_service import ComplaintService
from app.services.triage_service import TriageOrchestrator


def get_complaint_repository(
    session: Annotated[AsyncSession, Depends(get_db)],
) -> ComplaintRepository:
    return ComplaintRepository(session)


def get_triage(request: Request) -> TriageOrchestrator:
    orchestrator: TriageOrchestrator = request.app.state.triage  # built once in the lifespan
    return orchestrator


def get_complaint_service(
    repo: Annotated[ComplaintRepository, Depends(get_complaint_repository)],
    redis: Annotated[Redis, Depends(get_redis)],
    triage: Annotated[TriageOrchestrator, Depends(get_triage)],
) -> ComplaintService:
    return ComplaintService(repo, redis, triage)


Service = Annotated[ComplaintService, Depends(get_complaint_service)]
