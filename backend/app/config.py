from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# backend/app/config.py -> repository root, where the single shared .env lives
REPO_ROOT_ENV = Path(__file__).resolve().parents[2] / ".env"


class Settings(BaseSettings):
    ENVIRONMENT: str = "development"
    LOG_LEVEL: str = "INFO"

    # PostgreSQL 16 - required, never defaulted: credentials come from the environment only
    DATABASE_URL: str

    # Real environment variables always win over the file (Compose, Kubernetes, CI)
    model_config = SettingsConfigDict(env_file=REPO_ROOT_ENV, extra="ignore")


settings = Settings()  # type: ignore[call-arg]
