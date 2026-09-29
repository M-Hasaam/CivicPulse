# Triage: providers, caching, and what was actually measured

The AI layer's design decisions (why a `Protocol`, why the retry/fallback policy, why
`reporter_contact` is excluded) live in `docs/adr/0001-provider-interface.md` and
`docs/adr/0004-pii-and-data-governance.md`. This document is the narrower, more concrete
companion: what each provider actually does, and what was actually observed running it.

## The five providers

All five implement `TriageProvider.triage(text, location) -> TriageResult`
(`backend/app/providers/triage/base.py:31-34`) and are selected by `TRIAGE_PROVIDER`
via `factory.py`.

| `TRIAGE_PROVIDER` | Class | `name` | What it does |
| --- | --- | --- | --- |
| `auto` (default) | — | whichever hop answers | Not a provider itself — builds a chain out of the four below. See "Auto-detection" below. |
| `llm` | `LLMTriage` (`llm.py`) | `llm:groq` | Calls Groq's OpenAI-compatible chat API in JSON mode, `temperature=0`, with the shared retry/timeout policy from `http.py`. |
| `ollama` | `OllamaTriage` (`ollama.py`) | `llm:ollama` | Same system prompt and validator as `llm` (imports `SYSTEM_PROMPT`/`render_complaint` from `llm.py:10`) — only the transport and endpoint (`/api/chat` on a local Ollama server) differ. Fully offline: no complaint text ever leaves the machine. |
| `rules` | `RuleBasedTriage` (`rules.py`) | `rules` | Deterministic keyword scoring across English + Roman-Urdu terms (`rules.py:10-31`), whole-word matched (`_whole_word`, line 43-45) so "waterfall" doesn't match "water". Urgency keywords (`URGENT`, line 33-38) force `priority=high`; the category with the most keyword hits wins, `Category.other` if nothing matched. This is also the always-available last resort at the end of every chain. |
| `simulated` | `SimulatedTriage` (`simulated.py`) | `simulated` | CI/test-only. Seeded (`hashlib.sha256(f"{seed}:{text}")`, line 39) so the same input always produces the same confidence score, with `failure="raise"`/`"malformed"` to deterministically exercise the fallback and invalid-output paths in tests without any network call. |

## Auto-detection (`TRIAGE_PROVIDER=auto`)

`llm`/`ollama`/`rules`/`simulated` each pin exactly one provider, still falling back to
rules on a per-request failure (see below). `auto` is different: at **startup**
(`providers/triage/detect.py:detect_chain`, called once from `main.py`'s lifespan), it
builds an ordered chain out of whichever providers are actually usable, in this priority:

1. **Groq** — included only if `GROQ_API_KEY` is set *and* a real validation call
   (`check_groq_reachable`, a cheap `GET /models`, not a triage call) succeeds within
   `PROVIDER_DETECT_TIMEOUT_SECONDS` (default 3s).
2. **Ollama** — included only if `check_ollama_reachable` (`GET /api/tags`) succeeds
   within the same timeout. Confirms the server responds, not that the configured
   model is already pulled.
3. **Rules** — always appended last, unconditionally. It cannot fail, so the chain
   always has somewhere safe to land.

At request time, `TriageOrchestrator` walks the chain in order (`services/triage_service.py`):
whichever entry succeeds reports **its own name** as `triaged_by` — if Groq fails but
Ollama answers, that's `triaged_by: "llm:ollama"`, `fallback: false`, and it's cached
normally, because it's a real AI answer, not a degraded one. `fallback: true` /
`triaged_by: "rules:fallback"` is reported only when rules answers *because everything
ahead of it in the chain failed* — the same meaning `rules:fallback` already had before
`auto` existed.

Detection runs once per process; a container restart re-evaluates it. There's no
periodic re-check, so if Ollama comes up after the backend has already started with
`auto` and skipped it, a restart is needed to pick it up.

`llm` and `ollama` share one prompt (`llm.py:16-31`) that delimits the complaint as untrusted
data (`<complaint>...</complaint>`, angle brackets escaped, `llm.py:34-40`) — a
prompt-injection defense, tested directly by
`backend/tests/test_api.py::test_prompt_injection_cannot_choose_the_category` (lines
136-164), which submits a complaint attempting to override the category and asserts the
response still only contains a schema-valid enum value, decided by validation rather than by
attacker-controlled text.

## Content-hash caching

`backend/app/cache/triage_cache.py`: the cache key is `sha256(lowercased, whitespace-collapsed
text)` (`triage_key`, lines 17-20) — two complaints differing only in casing or extra spaces
hit the same cache entry — with a 24h TTL (`TRIAGE_TTL_SECONDS`, line 11). Only non-fallback
results are ever stored (enforced at the call site,
`services/triage_service.py:47-54`): caching a `rules:fallback` answer would pin a degraded
result for a full day after the primary provider recovers. A Redis read/write failure or a
corrupted entry is treated as a plain cache miss, never a 500 (lines 32-44).

## What was actually measured

Ran locally (`docker compose --env-file .env -f compose.yaml up -d postgres redis migrate
seed backend`, `TRIAGE_PROVIDER=rules` for a fast, deterministic demo run) — submitted the
same complaint text twice via `POST /api/complaints`:

- **First submission**: `"triaged_by": "rules"`, `"triage_latency_ms": 4` — a fresh triage,
  cache miss.
- **Second submission, identical text**: `"triaged_by": "rules"`, `"triage_latency_ms": 0` —
  served from the content-hash cache.
- **`GET /api/meta/providers`** after both:
  ```json
  {
    "active_provider": "rules",
    "recent_outcomes": [
      {"provider": "rules", "latency_ms": 0, "fallback": false, "cached": true},
      {"provider": "rules", "latency_ms": 4, "fallback": false, "cached": false},
      {"provider": "llm:groq", "latency_ms": 681, "fallback": false, "cached": false}
    ],
    "triage_cache": {"hits": 1, "misses": 2, "hit_rate": 0.333}
  }
  ```
  The third entry (`llm:groq`, 681ms) is a real earlier call against the hosted model,
  persisted from a prior session in Redis's AOF-backed volume — left in place rather than
  wiped, since it's genuine evidence of the hosted path having actually run, not just the
  rules path. **Measured hit rate at time of writing: 1/3 = 0.333** over this small sample;
  it climbs toward the duplicate-complaint rate in practice (the brief's own framing: "a burst
  main gets reported by nine neighbours" — nine duplicates cost one inference instead of
  nine once the first is cached).

This is a live, dynamic number — re-running `GET /api/meta/providers` after more traffic will
report a different one. `triage_latency_ms` is recorded per outcome
(`services/triage_service.py:114-115`) and is what makes both this table and the brief's
"report your measured hit rate" requirement something you can actually observe rather than
estimate.
