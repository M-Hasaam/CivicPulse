# ADR 0004: What leaves this machine when a complaint is triaged, to whom, and why

## Status
Accepted

## Context

A citizen complaint's `text` and `location` can contain names, addresses, and identifying
detail ("burst main outside 14 Iqbal Road, my kids can't get to school"). The brief requires
this to be a stated engineering decision, not something left implicit: on Groq's free tier,
Google/Groq may use submitted input to improve their models, and `reporter_contact`
(phone/email) is the most sensitive field in the schema.

## Decision

Two separate calls, one architectural and one operational:

**`reporter_contact` never leaves this process.** `TriageProvider.triage(self, text, location)`
(`backend/app/providers/triage/base.py:31-34`) does not accept a contact field — it is
structurally impossible for `LLMTriage` (or any provider) to send it to Groq, because the
orchestrator (`services/triage_service.py:41`, `90-96`) never has it to pass in the first
place. This is enforced by the type signature, not by a reviewer remembering to redact it.

**`text` and `location` are sent to Groq as-is when `TRIAGE_PROVIDER=llm`** — we chose
*accept and document the exposure*, not redact-before-send, for three reasons: (1) redaction
that's good enough to catch every name/address pattern in free-text, Urdu-influenced English
is itself an unsolved NLP problem — a naive regex redactor would either miss real PII or
mangle the complaint text the classifier needs to read; (2) the complaint is already visible
to city operations staff by design (that's the point of the system) and treated as
operational data, not a secret, once submitted; (3) `llm.py:34-40` still delimits it as
untrusted *data* (`<complaint>...</complaint>`, angle-brackets escaped) — that's a
prompt-injection defense, deliberately not a confidentiality one, and the two are not the
same problem.

Two mitigations reduce actual exposure without redaction:
- **`TRIAGE_PROVIDER=ollama`** (`providers/triage/ollama.py`) is a fully offline path — no
  complaint text leaves the machine at all. It's a real, working provider (not a stub),
  selectable by the same environment variable as every other provider (ADR 0001), for any
  deployment where sending complaint text to a third party is unacceptable.
- **`TRIAGE_PROVIDER=simulated` in CI** (`.github/workflows/ci.yml:26`) means the test suite
  never sends real or synthetic PII to any external service, on every single run.
- **`GROQ_API_KEY` is never logged**: it arrives via `SecretStr` (`llm.py:6,48,56`, using
  Pydantic's secret-value wrapper so it can't accidentally end up in a repr or log line), is
  read from the environment (`app/config.py`, sourced from a Kubernetes Secret / GitHub
  Secret — see `k8s/base/kustomization.yaml`'s `secretGenerator`), and is never written to the
  repository.

## Consequences

- Anyone deploying with `TRIAGE_PROVIDER=llm` in a jurisdiction or context where sending
  citizen-submitted free text to a US-hosted third party is not acceptable must switch to
  `ollama` or `rules` — that's a one-environment-variable operational decision, not a code
  change, precisely because of ADR 0001's interface.
- `reporter_contact` is retained in Postgres and shown to operations staff (its intended
  use), but is categorically excluded from the one place in the system that talks to a third
  party. That guarantee costs nothing to maintain going forward — there's no `reporter_contact`
  parameter anywhere in the triage path to accidentally start passing through.
- This ADR does not claim `text`/`location` are non-sensitive — they can contain PII. The
  claim is narrower: the exposure is a stated, deliberate tradeoff with two documented ways to
  avoid it entirely, not an oversight.
