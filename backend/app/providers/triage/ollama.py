"""Fully offline triage against a local Ollama server. Same prompt, same
validator and same call policy as the hosted LLM - only the transport differs."""

import asyncio

import httpx

from app.providers.triage.base import InvalidTriageOutputError, TriageResult, parse_triage_output
from app.providers.triage.http import Sleep, post_json
from app.providers.triage.llm import SYSTEM_PROMPT, render_complaint


class OllamaTriage:
    name = "llm:ollama"

    def __init__(
        self,
        base_url: str,
        model: str,
        timeout_seconds: float = 10.0,
        transport: httpx.AsyncBaseTransport | None = None,
        sleep: Sleep = asyncio.sleep,
    ) -> None:
        self._url = base_url.rstrip("/") + "/api/chat"
        self._model = model
        self._timeout = timeout_seconds
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
            transport=self._transport,
            sleep=self._sleep,
        )
        try:
            content = body["message"]["content"]
        except (KeyError, TypeError) as exc:
            raise InvalidTriageOutputError(f"unexpected response shape: {exc!r}") from exc
        return parse_triage_output(content)
