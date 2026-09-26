# CivicPulse

Municipal complaint intake, AI triage and operations platform.

A citizen submits a free-text complaint; the backend triages it with an LLM into a
category, a priority and a one-line summary, persists it, and surfaces it on an
operations dashboard.

> Work in progress. This README covers local development only; the one-command
> Docker Compose quickstart will replace it once the stack is containerised.

## Stack

- **Backend:** FastAPI + Pydantic v2 (Python 3.12)
- **Frontend:** React 18 + Vite + TypeScript

## Run the backend locally

Requires Python 3.12. From the repository root (PowerShell):

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
uvicorn app.main:app --reload
```

On macOS/Linux, activate with `source .venv/bin/activate` instead.

| URL | Purpose |
| --- | --- |
| http://localhost:8000/ | Hello endpoint |
| http://localhost:8000/health | Liveness probe (never touches the database) |
| http://localhost:8000/metrics | Prometheus metrics |
| http://localhost:8000/docs | Interactive OpenAPI docs |

### Lint and type-check

```powershell
ruff check .
mypy app
```
