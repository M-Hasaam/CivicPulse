from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# backend/app/config.py -> repository root, where the single shared .env lives
REPO_ROOT_ENV = Path(__file__).resolve().parents[2] / ".env"


class Settings(BaseSettings):
    ENVIRONMENT: str = "development"
    LOG_LEVEL: str = "INFO"

    # PostgreSQL 16 - required, never defaulted: credentials come from the environment only
    DATABASE_URL: str

    # Redis 7 - cache and rate limiter. No credentials in the local default.
    REDIS_URL: str = "redis://localhost:6379/0"

    # Fixed-window limit per client on POST /api/complaints
    RATE_LIMIT_MAX_REQUESTS: int = 10
    RATE_LIMIT_WINDOW_SECONDS: int = 60

    # Reverse proxies we control in front of the backend (nginx, ingress). Only the
    # X-Forwarded-For entries they append are trusted; 0 ignores the header entirely.
    TRUSTED_PROXY_HOPS: int = 1

    # Real environment variables always win over the file (Compose, Kubernetes, CI)
    model_config = SettingsConfigDict(env_file=REPO_ROOT_ENV, extra="ignore")


settings = Settings()  # type: ignore[call-arg]
