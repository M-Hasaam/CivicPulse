# AI Usage

Section 5.5 of the brief asks for honest attribution: which AI tools we used,
which parts they wrote or shaped, and what we changed afterwards and why. This
file is updated with every feature branch.

## Tools

| Tool | Used by | Used for |
| --- | --- | --- |
| Claude Code (Claude Opus 5.5), VS Code extension | Hasaam | Writing and verifying backend code, repository/branch workflow, README and docs |
| GitHub Copilot pull-request reviewer | Both (automatic) | Automated review comments on every PR |
| _to be filled in by Burhan_ | Burhan | |

Commits Claude Code helped write carry a
`Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>` trailer, so
`git log --grep "Co-Authored-By: Claude"` lists them.

## History of how the code was produced

1. **First prototype (discarded as history).** Claude Code generated a complete
   first version of the whole system in one pass, committed as a single
   "first commit". An audit against the brief found real defects in it:
   - the backend could not be installed (`pip install .` failed on setuptools discovery)
   - the Ollama provider crashed on every call (`false` instead of `False`)
   - migrations were never run
   - the Kubernetes `namePrefix` broke service DNS
   - `Retry-After` was dropped on 429
   - validation returned 422 instead of 400
   - the test mocks were ineffective
   - there was no ESLint config

   Trivy never failed and the integration job asserted nothing. The engineering
   notes also claimed HPA measurements that had never been taken.
2. **Rebuild.** We reset `main` to the assignment brief only and rebuilt
   the project in small, reviewed steps on feature branches, fixing those defects
   as we went. The prototype is used as reference material, not copied wholesale.

## Per-feature record

### Backend scaffold, config, health and metrics (#2, #6)
- **AI:** Claude Code wrote the FastAPI scaffold, settings, `/health` and `/metrics`.
- **Changed:** We trimmed `config.py` and `.env.example` to only the settings in
  use (#6), removing a hardcoded default database password.

### Data layer (#10)
- **AI:** Claude Code wrote the model, Alembic migration, repository, seed and
  `/ready`, and verified them against a real Postgres 16 container.
- **Changed after human review:**
  - We moved domain enums to `app/domain.py` so repositories do not depend on providers.
  - `.env` is now loaded from the repo root.
  - Burhan's review led to three more changes: an `id` tie-breaker for
    pagination, `other`-category seed rows, and README notes for restarting the
    dev container.

### Triage providers (#18)
- **AI:** Claude Code wrote the provider interface, the rules, simulated, Groq and
  Ollama providers, the retry/timeout helper and the tests. It checked each
  retry rule against a mock server and made live Groq calls.
- **Changed after review:**
  - The live call showed `llama-3.1-8b-instant` had been retired, so we switched
    to `openai/gpt-oss-20b`.
  - Copilot's review and Burhan's led to five more changes:
    - strict `confidence` and single-line summaries
    - a hard per-attempt deadline
    - a `TriageError` for malformed 2xx bodies
    - whole-word keyword matching
    - a `rules` default in `.env.example`
  - The merge conflict with #16 was resolved by hand. See
    `docs/evidence/MERGE-CONFLICT.md`.

### Complaints API (#19)
- **AI:** Claude Code wrote the state machine, the triage orchestrator, the
  complaint service, the routes, JSON logging, the lifespan-managed clients and
  the tests. It checked the flow live against Postgres, Redis and Groq.
- **Decisions we made:**
  - Cache results only from the configured provider, and never the fallback.
  - Keep triage outcomes and hit/miss counts in Redis so all pods agree.
  - Label request metrics by route template.
  - Move the Redis client into the lifespan, which fixes the event-loop issue
    found while reviewing #16.

### Frontend scaffold (#9)
- _To be filled in by Burhan._
