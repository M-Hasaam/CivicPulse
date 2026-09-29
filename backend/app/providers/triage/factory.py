import httpx

from app.config import Settings
from app.providers.triage.base import TriageProvider
from app.providers.triage.detect import detect_chain
from app.providers.triage.llm import LLMTriage
from app.providers.triage.ollama import OllamaTriage
from app.providers.triage.rules import RuleBasedTriage
from app.providers.triage.simulated import SimulatedTriage


async def build_triage_chain(
    settings: Settings, http_client: httpx.AsyncClient | None = None
) -> list[TriageProvider]:
    """Build the ordered provider chain named by TRIAGE_PROVIDER. Nothing else in
    the system knows or cares which provider(s) it contains, or how many."""
    match settings.TRIAGE_PROVIDER:
        case "auto":
            if http_client is None:
                raise ValueError("TRIAGE_PROVIDER=auto requires a shared http_client")
            return await detect_chain(settings, http_client)
        case "llm":
            return [
                LLMTriage(
                    api_key=settings.GROQ_API_KEY,
                    model=settings.GROQ_MODEL,
                    timeout_seconds=settings.TRIAGE_TIMEOUT_SECONDS,
                    client=http_client,
                ),
                RuleBasedTriage(),
            ]
        case "ollama":
            return [
                OllamaTriage(
                    base_url=settings.OLLAMA_BASE_URL,
                    model=settings.OLLAMA_MODEL,
                    timeout_seconds=settings.TRIAGE_TIMEOUT_SECONDS,
                    client=http_client,
                ),
                RuleBasedTriage(),
            ]
        case "simulated":
            return [
                SimulatedTriage(
                    failure=settings.SIMULATED_TRIAGE_FAILURE, seed=settings.SIMULATED_TRIAGE_SEED
                ),
                RuleBasedTriage(),
            ]
        case "rules":
            return [RuleBasedTriage()]
