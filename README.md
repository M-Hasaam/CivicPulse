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

### 1. Start a local PostgreSQL 16

Until Docker Compose lands, run Postgres in a throwaway container:

```powershell
docker run -d --name civicpulse-dev-pg `
  -e POSTGRES_USER=civicpulse -e POSTGRES_PASSWORD=change_me -e POSTGRES_DB=civicpulse `
  -p 5432:5432 postgres:16-alpine
```

That creates the container once. Afterwards, start and stop the same one
(`docker run` again fails with "name already in use"):

```powershell
docker start civicpulse-dev-pg
docker stop civicpulse-dev-pg
```

### 2. Configure

Copy `.env.example` to `.env` in the repository root. Its `DATABASE_URL` already
points at the container above. The backend reads the root `.env` from any
working directory; real environment variables override it.

### 3. Install, migrate, seed, run

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
alembic upgrade head             # create the schema (never done at app startup)
python -m app.seed               # 30 demo complaints; safe to run again
python -m uvicorn app.main:app --reload
```

On macOS/Linux, activate with `source .venv/bin/activate` instead.

| URL | Purpose |
| --- | --- |
| http://localhost:8000/ | Hello endpoint |
| http://localhost:8000/health | Liveness probe (never touches the database) |
| http://localhost:8000/ready | Readiness probe: 200 when Postgres is reachable, 503 naming it otherwise |
| http://localhost:8000/metrics | Prometheus metrics |
| http://localhost:8000/docs | Interactive OpenAPI docs |

### Lint, type-check and test

```powershell
ruff check .
mypy app
pytest
```
