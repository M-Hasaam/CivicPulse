from typing import Any

from fastapi import APIRouter, Response, status
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest

from app.cache.client import ping_redis
from app.repositories.database import ping_database

router = APIRouter(tags=["observability"])

# Prometheus Metrics
REQUEST_COUNT = Counter(
    "civicpulse_http_requests_total",
    "Total HTTP requests received",
    ["method", "endpoint", "status_code"],
)
REQUEST_LATENCY = Histogram(
    "civicpulse_http_request_duration_seconds",
    "HTTP request latency in seconds",
    ["method", "endpoint"],
)


@router.get("/health", status_code=status.HTTP_200_OK)
async def liveness() -> dict[str, str]:
    """
    Liveness probe: confirms the process is alive.
    Must NOT touch the database or external services to prevent cascading restart loops.
    """
    return {"status": "ok", "probe": "liveness"}


@router.get("/ready")
async def readiness(response: Response) -> dict[str, Any]:
    """
    Readiness probe: 200 only when every dependency is reachable,
    otherwise 503 naming the dependency that failed.
    """
    failed: list[str] = []

    try:
        await ping_database()
    except Exception as exc:  # any failure means "not ready", never a crash
        failed.append(f"postgres ({type(exc).__name__})")

    try:
        await ping_redis()
    except Exception as exc:
        failed.append(f"redis ({type(exc).__name__})")

    if failed:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return {"status": "unready", "failed_dependencies": failed}
    return {"status": "ready"}


@router.get("/metrics")
async def metrics() -> Response:
    """
    Prometheus metrics exposition endpoint.
    """
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)
