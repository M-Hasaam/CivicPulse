from pathlib import Path

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

# backend/app/config.py -> repository root, where the single shared .env lives
REPO_ROOT_ENV = Path(__file__).resolve().parents[2] / ".env"


class Settings(BaseSettings):
    ENVIRONMENT: str = "development"
    LOG_LEVEL: str = "INFO"

    # PostgreSQL 16 - required, never defaulted: credentials come from the environment only
    DATABASE_URL: str

    # AI triage. SecretStr keeps the key out of repr() and logs.
    GROQ_API_KEY: SecretStr = SecretStr("")
    GROQ_MODEL: str = "llama-3.1-8b-instant"
    TRIAGE_TIMEOUT_SECONDS: float = 10.0

    # Real environment variables always win over the file (Compose, Kubernetes, CI)
    model_config = SettingsConfigDict(env_file=REPO_ROOT_ENV, extra="ignore")


settings = Settings()  # type: ignore[call-arg]
