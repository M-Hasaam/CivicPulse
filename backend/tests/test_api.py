"""End-to-end HTTP tests: real routes, service, triage orchestration and caches,
with an in-memory repository, fakeredis and a deterministic provider."""

from collections.abc import AsyncIterator
from dataclasses import dataclass

import httpx
import pytest
from redis.asyncio import Redis

from app.cache.client import get_redis
from app.dependencies import get_complaint_repository, get_triage
from app.main import app
from app.providers.triage.base import TriageProvider
from app.providers.triage.simulated import SimulatedTriage
from app.services.triage_service import TriageOrchestrator
from tests.fakes import FakeComplaintRepository

pytestmark = pytest.mark.anyio

VALID = {"text": "Transformer sparking near the school gate", "location": "F-6/1"}


@dataclass
class Api:
    client: httpx.AsyncClient
    repo: FakeComplaintRepository
    redis: Redis

    def use_provider(self, provider: TriageProvider) -> None:
        app.dependency_overrides[get_triage] = lambda: TriageOrchestrator(provider)


@pytest.fixture
async def api(redis: Redis) -> AsyncIterator[Api]:
    repo = FakeComplaintRepository()
    app.dependency_overrides[get_redis] = lambda: redis
    app.dependency_overrides[get_complaint_repository] = lambda: repo
    app.dependency_overrides[get_triage] = lambda: TriageOrchestrator(SimulatedTriage())
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        yield Api(client, repo, redis)
    app.dependency_overrides.clear()


# --- validation: 400 with field-level errors --------------------------------------------------


async def test_invalid_body_is_400_naming_each_field(api: Api) -> None:
    response = await api.client.post("/api/complaints", json={"text": "too short", "location": "x"})
    assert response.status_code == 400
    body = response.json()
    assert body["detail"] == "Validation failed"
    assert {e["field"] for e in body["errors"]} == {"text", "location"}
    assert all(e["in"] == "body" and e["message"] for e in body["errors"])


async def test_whitespace_does_not_count_towards_minimum_length(api: Api) -> None:
    response = await api.client.post(
        "/api/complaints", json={"text": "   short   " + " " * 20, "location": "F-6"}
    )
    assert response.status_code == 400
    assert [e["field"] for e in response.json()["errors"]] == ["text"]


async def test_unknown_fields_are_rejected(api: Api) -> None:
    response = await api.client.post(
        "/api/complaints", json={**VALID, "category": "other", "priority": "low"}
    )
    assert response.status_code == 400  # citizens cannot pick their own triage


async def test_query_and_path_errors_are_400_too(api: Api) -> None:
    assert (await api.client.get("/api/complaints?page_size=101")).status_code == 400
    assert (await api.client.get("/api/complaints?status=closed")).status_code == 400
    assert (await api.client.get("/api/complaints/not-a-uuid")).status_code == 400


async def test_openapi_documents_400_and_not_422() -> None:
    schema = app.openapi()
    post = schema["paths"]["/api/complaints"]["post"]["responses"]
    assert "400" in post and "422" not in post
