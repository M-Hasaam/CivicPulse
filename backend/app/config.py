from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    ENVIRONMENT: str = "development"
    LOG_LEVEL: str = "INFO"

    # Server
    BACKEND_HOST: str = "0.0.0.0"
    BACKEND_PORT: int = 8000

    # PostgreSQL 16
    DATABASE_URL: str = "postgresql+asyncpg://civicpulse:civicpulse_secret_change_me@postgres:5432/civicpulse"

    # Redis 7
    REDIS_URL: str = "redis://redis:6379/0"

    # AI Triage
    TRIAGE_PROVIDER: Literal["llm", "ollama", "rules", "simulated"] = "simulated"
    GROQ_API_KEY: str = ""
    GROQ_MODEL: str = "llama-3.1-8b-instant"
    GEMINI_API_KEY: str = ""
    OLLAMA_BASE_URL: str = "http://ollama:11434"
    OLLAMA_MODEL: str = "llama3.2:1b"

    # Rate Limiting
    RATE_LIMIT_REQUESTS_PER_MINUTE: int = 15

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
