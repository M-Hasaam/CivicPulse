"""TRIAGE_PROVIDER=auto: the startup detection chain (Groq -> Ollama -> rules)."""

from collections.abc import Callable

import httpx
import pytest
from pydantic import SecretStr

from app.config import Settings
from app.providers.triage.detect import detect_chain
from app.providers.triage.factory import build_triage_chain
from app.providers.triage.llm import LLMTriage, check_groq_reachable
from app.providers.triage.ollama import OllamaTriage, check_ollama_reachable
from app.providers.triage.rules import RuleBasedTriage

pytestmark = pytest.mark.anyio

GROQ_KEY = SecretStr("gsk_test_key")

Handler = Callable[[httpx.Request], httpx.Response]


def _settings(**overrides: object) -> Settings:
    return Settings(
        DATABASE_URL="x",
        TRIAGE_PROVIDER="auto",
        _env_file=None,
        **overrides,  # type: ignore[arg-type]
    )  # type: ignore[call-arg]


def _client(handler: Handler) -> httpx.AsyncClient:
    return httpx.AsyncClient(transport=httpx.MockTransport(handler))


def _failing(exc: Exception) -> Handler:
    def handler(request: httpx.Request) -> httpx.Response:
        raise exc

    return handler


def _routed(*, groq: httpx.Response | Exception, ollama: httpx.Response | Exception) -> Handler:
    def handler(request: httpx.Request) -> httpx.Response:
        reply = groq if request.url.host == "api.groq.com" else ollama
        if isinstance(reply, Exception):
            raise reply
        return reply

    return handler


# --- check_groq_reachable ----------------------------------------------------------------------


async def test_groq_unreachable_when_no_key_is_set() -> None:
    # No network call at all - an empty key is never worth a request.
    assert not await check_groq_reachable(
        SecretStr(""), client=_client(lambda r: httpx.Response(200))
    )


async def test_groq_reachable_on_a_successful_validation_call() -> None:
    client = _client(lambda r: httpx.Response(200, json={"data": []}))
    assert await check_groq_reachable(GROQ_KEY, client=client)


async def test_groq_unreachable_on_an_error_response() -> None:
    client = _client(lambda r: httpx.Response(401))
    assert not await check_groq_reachable(GROQ_KEY, client=client)


async def test_groq_unreachable_on_a_connection_failure() -> None:
    client = _client(_failing(httpx.ConnectError("refused")))
    assert not await check_groq_reachable(GROQ_KEY, client=client)


# --- check_ollama_reachable --------------------------------------------------------------------


async def test_ollama_reachable_on_a_successful_response() -> None:
    client = _client(lambda r: httpx.Response(200, json={"models": []}))
    assert await check_ollama_reachable("http://ollama:11434", client=client)


async def test_ollama_unreachable_on_a_connection_failure() -> None:
    client = _client(_failing(httpx.ConnectError("refused")))
    assert not await check_ollama_reachable("http://ollama:11434", client=client)


# --- detect_chain -------------------------------------------------------------------------------


async def test_both_available_builds_groq_then_ollama_then_rules() -> None:
    client = _client(_routed(groq=httpx.Response(200), ollama=httpx.Response(200)))
    chain = await detect_chain(_settings(GROQ_API_KEY="gsk_test_key"), client)
    assert [type(p) for p in chain] == [LLMTriage, OllamaTriage, RuleBasedTriage]


async def test_only_groq_available() -> None:
    client = _client(_routed(groq=httpx.Response(200), ollama=httpx.ConnectError("refused")))
    chain = await detect_chain(_settings(GROQ_API_KEY="gsk_test_key"), client)
    assert [type(p) for p in chain] == [LLMTriage, RuleBasedTriage]


async def test_only_ollama_available() -> None:
    client = _client(_routed(groq=httpx.Response(401), ollama=httpx.Response(200)))
    chain = await detect_chain(_settings(), client)  # no GROQ_API_KEY set
    assert [type(p) for p in chain] == [OllamaTriage, RuleBasedTriage]


async def test_neither_available_is_rules_only() -> None:
    client = _client(
        _routed(groq=httpx.ConnectError("refused"), ollama=httpx.ConnectError("refused"))
    )
    chain = await detect_chain(_settings(), client)
    assert [type(p) for p in chain] == [RuleBasedTriage]


# --- build_triage_chain routes "auto" to detect_chain -------------------------------------------


async def test_build_triage_chain_routes_auto_to_detection() -> None:
    client = _client(_routed(groq=httpx.Response(200), ollama=httpx.ConnectError("refused")))
    chain = await build_triage_chain(_settings(GROQ_API_KEY="gsk_test_key"), client)
    assert [type(p) for p in chain] == [LLMTriage, RuleBasedTriage]


async def test_build_triage_chain_rejects_auto_without_a_shared_client() -> None:
    with pytest.raises(ValueError, match="shared http_client"):
        await build_triage_chain(_settings(), http_client=None)
