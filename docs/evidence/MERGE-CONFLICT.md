# Deliberate merge conflict: triage settings vs Redis settings

**Branches:** `feature/triage-providers` (Hasaam, PR #18) and `feature/redis-cache` (Burhan, PR #16).
**Merge commit:** `680cd47`, "Merge origin/dev into feature/triage-providers".

## What conflicted

Both branches added new configuration in the same place, right after
`DATABASE_URL`, and a new dependency right after `alembic`:

| File | This branch (HEAD) | `dev` after #16 (incoming) |
| --- | --- | --- |
| `backend/app/config.py` | `TRIAGE_PROVIDER`, `GROQ_*`, `OLLAMA_*`, `TRIAGE_TIMEOUT_SECONDS`, `SIMULATED_TRIAGE_*` | `REDIS_URL`, `RATE_LIMIT_*`, `TRUSTED_PROXY_HOPS` |
| `.env.example` | the matching triage variables | the matching Redis and rate-limit variables |
| `backend/pyproject.toml` | `httpx` | `redis` |

PR #16 merged into `dev` first. Merging `dev` into this branch then stopped
with conflicts in all three files.

## Evidence

1. `merge-conflict-1-markers-env-example.png`: conflict markers in `.env.example`
2. `merge-conflict-2-markers-pyproject.png`: conflict markers in `pyproject.toml`
3. `merge-conflict-3-markers-config.png`: conflict markers in `config.py`
4. `merge-conflict-4-resolved-config.png`: `config.py` in the merge commit's diff (triage settings kept, Redis group added below them, no markers left)
5. `merge-conflict-5-merge-commit.png`: merge commit `680cd47` in PR #18, with its message describing the conflict and resolution

The same evidence, reproducible from the repository:

```text
*   680cd47 Muhammad Hasaam: Merge origin/dev into feature/triage-providers
|\
| *   e713fc4 Muhammad Hasaam: Merge pull request #16 from M-Hasaam/feature/redis-cache
| |\
| | * 2db673c Burhan Ahmed: fix(cache): use 30s TTL for the stats cache
| | * 7d6b607 Burhan Ahmed: fix(cache): trust only proxy-appended X-Forwarded-For entries
| | * 99f7ae6 Burhan Ahmed: docs: document local Redis alongside Postgres
| | * c3c75a5 Burhan Ahmed: test(cache): rate limiter and cache tests
```

Only the three conflicted files differ from **both** parents, i.e. only they were edited by hand. Every other file in the merge came from #16 unchanged:

```text
$ git diff-tree --cc --name-only 680cd47
.env.example
backend/app/config.py
backend/pyproject.toml
```

## Why this resolution won

Neither side replaced the other: each branch added settings its own code
needs. Taking only "current" would have deleted `REDIS_URL` and broken the
cache, limiter and `/ready`. Taking only "incoming" would have deleted
`TRIAGE_PROVIDER` and the Groq key and broken provider selection. So we kept
both and grouped them by feature, triage first and Redis second, each under
its own comment, so the settings class still reads as one section per
subsystem. We then ran both test suites together (63 passed) and checked
`/ready` against live Postgres and Redis before committing the merge, rather
than trusting that the text merge was correct.
