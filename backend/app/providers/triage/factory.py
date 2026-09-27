from app.config import Settings
from app.providers.triage.base import TriageProvider
from app.providers.triage.llm import LLMTriage
from app.providers.triage.ollama import OllamaTriage
from app.providers.triage.rules import RuleBasedTriage
from app.providers.triage.simulated import SimulatedTriage


def get_triage_provider(settings: Settings) -> TriageProvider:
    """Select the provider named by TRIAGE_PROVIDER. Nothing else in the
    system knows or cares which one it is."""
    match settings.TRIAGE_PROVIDER:
        case "llm":
            return LLMTriage(
                api_key=settings.GROQ_API_KEY,
                model=settings.GROQ_MODEL,
                timeout_seconds=settings.TRIAGE_TIMEOUT_SECONDS,
            )
        case "ollama":
            return OllamaTriage(
                base_url=settings.OLLAMA_BASE_URL,
                model=settings.OLLAMA_MODEL,
                timeout_seconds=settings.TRIAGE_TIMEOUT_SECONDS,
            )
        case "simulated":
            return SimulatedTriage(
                failure=settings.SIMULATED_TRIAGE_FAILURE, seed=settings.SIMULATED_TRIAGE_SEED
            )
        case "rules":
            return RuleBasedTriage()
