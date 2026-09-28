from pathlib import Path
from typing import Literal

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

# backend/app/config.py -> repository root, where the single shared .env lives
REPO_ROOT_ENV = Path(__file__).resolve().parents[2] / ".env"


class Settings(BaseSettings):
    ENVIRONMENT: str = "development"
    LOG_LEVEL: str = "INFO"

    # PostgreSQL 16 - required, never defaulted: credentials come from the environment only
    DATABASE_URL: str

    # AI triage: llm (Groq) | ollama (offline) | rules | simulated (CI)
    TRIAGE_PROVIDER: Literal["llm", "ollama", "rules", "simulated"] = "rules"
    # SecretStr keeps the key out of repr() and logs.
    GROQ_API_KEY: SecretStr = SecretStr("")
    GROQ_MODEL: str = "openai/gpt-oss-20b"
    TRIAGE_TIMEOUT_SECONDS: float = 10.0
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "llama3.2:1b"
    SIMULATED_TRIAGE_FAILURE: Literal["none", "raise", "malformed"] = "none"
    SIMULATED_TRIAGE_SEED: int = 0

    # Redis 7 - cache and rate limiter. No credentials in the local default.
    REDIS_URL: str = "redis://localhost:6379/0"

    # Fixed-window limit per client on POST /api/complaints
    RATE_LIMIT_MAX_REQUESTS: int = 10
    RATE_LIMIT_WINDOW_SECONDS: int = 60

    # Reverse proxies we control in front of the backend (nginx, ingress). Only the
    # X-Forwarded-For entries they append are trusted; 0 ignores the header entirely.
    # Default is 0 (fail closed): compose.yaml, compose.prod.yaml and
    # k8s/base/kustomization.yaml each set this to 1 explicitly, since they're the
    # only topologies where a real proxy is actually in front of the backend. Any
    # other way of running this app - directly, with no proxy - must not silently
    # trust a client-supplied X-Forwarded-For.
    TRUSTED_PROXY_HOPS: int = 0

    # Real environment variables always win over the file (Compose, Kubernetes, CI)
    model_config = SettingsConfigDict(env_file=REPO_ROOT_ENV, extra="ignore")


settings = Settings()  # type: ignore[call-arg]
