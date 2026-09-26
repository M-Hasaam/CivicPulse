from fastapi import FastAPI

from app.config import settings

app = FastAPI(title="CivicPulse API")


@app.get("/")
async def root() -> dict[str, str]:
    return {"message": "Hello from CivicPulse", "environment": settings.ENVIRONMENT}
