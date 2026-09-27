import logging
import time
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

import httpx
from fastapi import FastAPI, Request, Response
from fastapi.openapi.utils import get_openapi

from app.cache.client import close_redis, connect_redis
from app.config import settings
from app.metrics import REQUEST_COUNT, REQUEST_LATENCY
from app.providers.triage.factory import get_triage_provider
from app.repositories.database import engine
from app.routes.complaints import router as complaints_router
from app.routes.errors import register_error_handlers
from app.routes.health import router as health_router
from app.routes.stats import router as stats_router
from app.services.triage_service import TriageOrchestrator

logger = logging.getLogger("civicpulse")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Create shared clients on the serving event loop; close them on shutdown.

    On SIGTERM uvicorn stops accepting connections and waits for in-flight
    requests to finish (bounded by --timeout-graceful-shutdown) before this
    shutdown half runs, so no request loses its Redis, HTTP or database pool.
    """
    connect_redis()
    http_client = httpx.AsyncClient(timeout=settings.TRIAGE_TIMEOUT_SECONDS)
    app.state.http_client = http_client
    app.state.triage = TriageOrchestrator(get_triage_provider(settings, http_client))
    logger.info("startup complete; triage provider %s", app.state.triage.provider.name)
    try:
        yield
    finally:
        logger.info("shutting down: closing HTTP, Redis and database pools")
        await http_client.aclose()
        await close_redis()
        await engine.dispose()
        logger.info("shutdown complete")


app = FastAPI(title="CivicPulse API", lifespan=lifespan)


@app.middleware("http")
async def metrics_middleware(request: Request, call_next) -> Response:  # type: ignore[no-untyped-def]
    start_time = time.perf_counter()
    response: Response = await call_next(request)
    duration = time.perf_counter() - start_time

    # Label by route template (/api/complaints/{complaint_id}), never the raw path:
    # one time series per URL would grow without bound.
    route = request.scope.get("route")
    endpoint = getattr(route, "path", "unmatched")
    REQUEST_COUNT.labels(
        method=request.method, endpoint=endpoint, status_code=str(response.status_code)
    ).inc()
    REQUEST_LATENCY.labels(method=request.method, endpoint=endpoint).observe(duration)
    return response


@app.get("/")
async def root() -> dict[str, str]:
    return {"message": "Hello from CivicPulse", "environment": settings.ENVIRONMENT}


register_error_handlers(app)
app.include_router(complaints_router)
app.include_router(stats_router)
app.include_router(health_router)


def _openapi_without_422() -> dict[str, Any]:
    """Validation errors are answered with 400 (see routes/errors.py), so drop the
    422 FastAPI documents by default - the typed frontend client reads this schema."""
    if app.openapi_schema is None:
        schema = get_openapi(title=app.title, version=app.version, routes=app.routes)
        for path in schema["paths"].values():
            for operation in path.values():
                operation.get("responses", {}).pop("422", None)
        app.openapi_schema = schema
    return app.openapi_schema


app.openapi = _openapi_without_422  # type: ignore[method-assign]
