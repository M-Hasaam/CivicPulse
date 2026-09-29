"""Auto-detection for TRIAGE_PROVIDER=auto: builds a priority chain out of whichever
AI providers are actually usable at startup - Groq first, then Ollama, then rules as
the guaranteed-safe last resort. Runs once, at process startup; a container restart
re-evaluates it - there is no periodic re-check during the process's lifetime."""

import logging

import httpx

from app.config import Settings
from app.providers.triage.base import TriageProvider
from app.providers.triage.llm import LLMTriage, check_groq_reachable
from app.providers.triage.ollama import OllamaTriage, check_ollama_reachable
from app.providers.triage.rules import RuleBasedTriage

logger = logging.getLogger(__name__)


async def detect_chain(settings: Settings, http_client: httpx.AsyncClient) -> list[TriageProvider]:
    chain: list[TriageProvider] = []

    if await check_groq_reachable(
        settings.GROQ_API_KEY,
        timeout_seconds=settings.PROVIDER_DETECT_TIMEOUT_SECONDS,
        client=http_client,
    ):
        chain.append(
            LLMTriage(
                api_key=settings.GROQ_API_KEY,
                model=settings.GROQ_MODEL,
                timeout_seconds=settings.TRIAGE_TIMEOUT_SECONDS,
                client=http_client,
            )
        )
    else:
        logger.warning("auto: Groq not usable (no key, or validation call failed) - skipping")

    if await check_ollama_reachable(
        settings.OLLAMA_BASE_URL,
        timeout_seconds=settings.PROVIDER_DETECT_TIMEOUT_SECONDS,
        client=http_client,
    ):
        chain.append(
            OllamaTriage(
                base_url=settings.OLLAMA_BASE_URL,
                model=settings.OLLAMA_MODEL,
                timeout_seconds=settings.TRIAGE_TIMEOUT_SECONDS,
                client=http_client,
            )
        )
    else:
        logger.warning("auto: Ollama not reachable at %s - skipping", settings.OLLAMA_BASE_URL)

    chain.append(RuleBasedTriage())
    logger.info("auto-detected triage chain: %s", " -> ".join(p.name for p in chain))
    return chain
