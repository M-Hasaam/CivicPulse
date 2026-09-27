# ADR 0001: TriageProvider as a Protocol, selected by environment variable

## Status
Accepted

## Context

The category/priority/summary judgment for a complaint has to be made by *something* that
reads free text, but the assignment brief is explicit that the "something" must be
replaceable: today a keyword rule, tomorrow a hosted LLM, later a fine-tuned classifier.
The system around it must not care which, and must not fall over when the current one is
rate-limited, slow, or wrong. Separately, the test suite has to be green on every run even
though a real LLM's output is not deterministic, and local development has to work with no
network and no API key at all.

## Decision

Every triage backend implements one `Protocol` (`backend/app/providers/triage/base.py:31-34`):

```python
class TriageProvider(Protocol):
    name: str
    async def triage(self, text: str, location: str) -> TriageResult: ...
```

Four implementations satisfy it — `LLMTriage` (Groq, `llm.py`), `OllamaTriage` (local model,
`ollama.py`), `RuleBasedTriage` (deterministic keywords, `rules.py`), `SimulatedTriage`
(deterministic fake with seeded/injectable failure, `simulated.py`) — and
`get_triage_provider()` (`factory.py:11-36`) selects one by matching `settings.TRIAGE_PROVIDER`
(`"llm" | "ollama" | "simulated" | "rules"`). Nothing outside `factory.py` imports a concrete
provider class; `TriageOrchestrator` (`services/triage_service.py:36-39`) and everything above
it only ever calls `self.provider.triage(...)` through the protocol.

The interface's signature is deliberately narrow: `text` and `location` only — no
`reporter_contact`. That is itself a decision, covered in ADR 0004.

Around the interface, one policy applies to every HTTP-based provider (`http.py:21-117`),
not duplicated per provider:
- A hard wall-clock timeout per attempt (`settings.TRIAGE_TIMEOUT_SECONDS`, default 10s),
  enforced with `asyncio.timeout` (`http.py:76`), not just httpx's own per-socket timeout.
- Exactly one retry, only for timeouts, `429`, or `5xx` (`_is_retryable`, `http.py:24-25`),
  after a jittered 0.5-1.5s pause (`http.py:109`). Any other `4xx` and connection failures
  raise immediately (`http.py:100-103`, `83-86`) — retrying a request that is wrong, or a
  host that is down, wastes the timeout budget on an outcome that will not change.
- Model output is *never* trusted because it parsed as JSON: `parse_triage_output`
  (`base.py:53-65`) validates it against `TriageResult`, a Pydantic model with
  `extra="forbid"` and `strict=True` on `confidence` (`base.py:11-19`) — prose, a code
  fence, an out-of-enum category, or a >140-char summary are rejected, never repaired.
- Any provider failure (timeout, malformed output, anything) is caught once, in
  `TriageOrchestrator._from_provider` (`triage_service.py:90-104`), and falls back to
  `RuleBasedTriage`, recording `triaged_by = "rules:fallback"` and the causing
  `error_class`. A user never sees a 500 because Groq was rate-limited.
- A fallback result is never cached (`triage_service.py:47-49`): caching content-hash → result
  for 24h (`cache/triage_cache.py`) is a real cost saving for duplicate complaints, but
  caching a fallback would pin a degraded answer for 24h after the real provider recovers.

CI pins `TRIAGE_PROVIDER=simulated` (`.github/workflows/ci.yml:26`) precisely so the test
suite's pass/fail is never a function of what a hosted model feels like answering today.

## Consequences

- Swapping providers, or adding a fifth, is a one-`case` change in `factory.py` and nothing
  else — routes, services, and tests are unaffected.
- The retry/timeout/fallback policy lives in exactly one place (`http.py`), so `LLMTriage`
  and `OllamaTriage` cannot drift out of sync on this behavior; `RuleBasedTriage` and
  `SimulatedTriage` don't need it at all (no network call to retry).
- The cost of this discipline: any *new* HTTP-based provider must be written to call
  through `post_json` rather than its own client code, or it silently loses the shared
  policy. Worth stating explicitly rather than assuming the next contributor notices.
