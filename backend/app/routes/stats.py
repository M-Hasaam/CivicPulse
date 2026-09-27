from fastapi import APIRouter, Response

from app.dependencies import Service
from app.schemas import ProviderMeta, StatsOut

router = APIRouter(prefix="/api", tags=["stats"])


@router.get("/stats")
async def get_stats(response: Response, service: Service) -> StatsOut:
    stats, cache_state = await service.stats()
    response.headers["X-Cache"] = cache_state  # HIT | MISS | BYPASS (Redis down)
    return StatsOut.model_validate(stats)


@router.get("/meta/providers")
async def provider_meta(service: Service) -> ProviderMeta:
    return ProviderMeta.model_validate(await service.provider_meta())
