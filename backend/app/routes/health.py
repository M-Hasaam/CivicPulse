from fastapi import APIRouter, Response, status
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest

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


@router.get("/metrics")
async def metrics() -> Response:
    """
    Prometheus metrics exposition endpoint.
    """
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)
