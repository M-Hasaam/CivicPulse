import time

from fastapi import FastAPI, Request, Response

from app.config import settings
from app.routes.health import REQUEST_COUNT, REQUEST_LATENCY
from app.routes.health import router as health_router

app = FastAPI(title="CivicPulse API")


@app.middleware("http")
async def metrics_middleware(request: Request, call_next) -> Response:  # type: ignore[no-untyped-def]
    start_time = time.perf_counter()
    response: Response = await call_next(request)
    duration = time.perf_counter() - start_time

    endpoint = request.url.path
    REQUEST_COUNT.labels(
        method=request.method, endpoint=endpoint, status_code=str(response.status_code)
    ).inc()
    REQUEST_LATENCY.labels(method=request.method, endpoint=endpoint).observe(duration)
    return response


@app.get("/")
async def root() -> dict[str, str]:
    return {"message": "Hello from CivicPulse", "environment": settings.ENVIRONMENT}


app.include_router(health_router)
