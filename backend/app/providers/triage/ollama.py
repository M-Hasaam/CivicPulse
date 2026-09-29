"""Fully offline triage against a local Ollama server. Same prompt, same
validator and same call policy as the hosted LLM - only the transport differs."""

import asyncio

import httpx

from app.providers.triage.base import InvalidTriageOutputError, TriageResult, parse_triage_output
from app.providers.triage.http import Sleep, post_json
from app.providers.triage.llm import SYSTEM_PROMPT, render_complaint


async def check_ollama_reachable(
    base_url: str,
    timeout_seconds: float = 3.0,
    client: httpx.AsyncClient | None = None,
) -> bool:
    """Confirms the Ollama server responds - not that the configured model is
    pulled yet. Only used by auto-detection at startup, never per-request."""
    url = base_url.rstrip("/") + "/api/tags"
    try:
        if client is not None:
            response = await client.get(url, timeout=timeout_seconds)
        else:
            async with httpx.AsyncClient(timeout=timeout_seconds) as own_client:
                response = await own_client.get(url)
    except httpx.HTTPError:
        return False
    return response.is_success


class OllamaTriage:
    name = "llm:ollama"

    def __init__(
        self,
        base_url: str,
        model: str,
        timeout_seconds: float = 10.0,
        client: httpx.AsyncClient | None = None,
        transport: httpx.AsyncBaseTransport | None = None,
        sleep: Sleep = asyncio.sleep,
    ) -> None:
        self._url = base_url.rstrip("/") + "/api/chat"
        self._model = model
        self._timeout = timeout_seconds
        self._client = client
        self._transport = transport
        self._sleep = sleep

    async def triage(self, text: str, location: str) -> TriageResult:
        body = await post_json(
            self._url,
            {
                "model": self._model,
                "stream": False,
                "format": "json",
                "options": {"temperature": 0},
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": render_complaint(text, location)},
                ],
            },
            provider=self.name,
            timeout_seconds=self._timeout,
            client=self._client,
            transport=self._transport,
            sleep=self._sleep,
        )
        try:
            content = body["message"]["content"]
        except (KeyError, TypeError) as exc:
            raise InvalidTriageOutputError(f"unexpected response shape: {exc!r}") from exc
        return parse_triage_output(content)
