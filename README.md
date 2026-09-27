# CivicPulse

Municipal complaint intake, AI triage and operations platform.

A citizen submits a free-text complaint; the backend triages it with an LLM into a
category, a priority and a one-line summary, persists it, and surfaces it on an
operations dashboard.

> Work in progress. This README covers local development only; the one-command
> Docker Compose quickstart will replace it once the stack is containerised.

## Stack

- **Backend:** FastAPI + Pydantic v2 (Python 3.12)
- **Database:** PostgreSQL 16, schema managed by Alembic
- **Frontend:** React 18 + Vite + TypeScript

## Run the backend locally

Requires Python 3.12. From the repository root (PowerShell):

### 1. Start a local PostgreSQL 16 and Redis 7

Until Docker Compose lands, run them in throwaway containers:

```powershell
docker run -d --name civicpulse-dev-pg `
  -e POSTGRES_USER=civicpulse -e POSTGRES_PASSWORD=change_me -e POSTGRES_DB=civicpulse `
  -p 5432:5432 postgres:16-alpine

docker run -d --name civicpulse-dev-redis -p 6379:6379 redis:7-alpine
```

That creates the containers once. Afterwards, start and stop the same ones
(`docker run` again fails with "name already in use"):

```powershell
docker start civicpulse-dev-pg civicpulse-dev-redis
docker stop civicpulse-dev-pg civicpulse-dev-redis
```

### 2. Configure

Copy `.env.example` to `.env` in the repository root. Its `DATABASE_URL` and `REDIS_URL` already
point at the containers above. The backend reads the root `.env` from any
working directory; real environment variables override it.

### 3. Install, migrate, seed, run

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
alembic upgrade head             # create the schema (never done at app startup)
python -m app.seed               # 32 demo complaints; safe to run again
python -m uvicorn app.main:app --reload
```

On macOS/Linux, activate with `source .venv/bin/activate` instead.

Open http://localhost:8000/docs for the interactive API.

## API

| Method | Path | Behaviour |
| --- | --- | --- |
| `POST` | `/api/complaints` | Validate, triage, persist. **201**; **400** with field-level errors; **429** with `Retry-After` over the rate limit |
| `GET` | `/api/complaints/{id}` | **200** / **404** |
| `GET` | `/api/complaints` | Filter by `category`, `priority`, `status`; paginate with `page`, `page_size` (≤ 100); returns `total` |
| `PATCH` | `/api/complaints/{id}/status` | Enforces the state machine; invalid transition → **409** naming it |
| `GET` | `/api/stats` | Counts by category, priority and status; Redis-cached 30 s; `X-Cache: HIT \| MISS` (`BYPASS` if Redis is down) |
| `GET` | `/api/meta/providers` | Active provider, last 20 triage outcomes (provider, latency, fallback, cached) and the triage cache hit rate |
| `GET` | `/health` | Liveness: process alive, never touches a dependency |
| `GET` | `/ready` | Readiness: 200 only if Postgres and Redis answer; 503 naming what failed |
| `GET` | `/metrics` | Prometheus: request count and latency, triage latency, fallbacks, triage cache hits |

**Status machine:** `open → in_progress → resolved`, `open → rejected`,
`in_progress → rejected`. `resolved` and `rejected` are final.

**Triage:** `TRIAGE_PROVIDER` selects `llm` (Groq), `ollama`, `rules` or
`simulated`. Any provider failure (timeout, 429, 5xx, malformed output) falls
back to the keyword rules and is recorded as `triaged_by = rules:fallback`.
Duplicate complaints are served from a 24 h content-hash cache.

```powershell
curl -X POST http://localhost:8000/api/complaints -H "Content-Type: application/json" `
  -d '{"text": "Burst water main flooding Street 12 since fajr", "location": "G-10/4"}'
```

Every response carries an `X-Request-ID` (yours if you send one). Logs are JSON
on stdout, one line per event, each with that `request_id`.

### Lint, type-check and test

```powershell
ruff check .
mypy app
pytest --cov=app        # tests never call a live LLM
```
