# CivicPulse

Municipal complaint intake, AI triage and operations platform.

A citizen submits a free-text complaint; the backend triages it with an LLM into a
category, a priority and a one-line summary, persists it, and surfaces it on an
operations dashboard.


## Stack

- **Backend:** FastAPI + Pydantic v2 (Python 3.12)
- **Database:** PostgreSQL 16, schema managed by Alembic
- **Cache and rate limiter:** Redis 7
- **AI triage:** Groq (hosted), Ollama (offline) or keyword rules, behind one interface
- **Frontend:** React 18 + Vite + TypeScript

## Quickstart (Docker Compose)

Needs only Docker Desktop.

```powershell
git clone https://github.com/M-Hasaam/CivicPulse.git
cd CivicPulse
Copy-Item .env.example .env      # macOS/Linux: cp .env.example .env
docker compose up -d --build --scale ollama=0 --scale ollama-pull=0
```

That starts the app with the default rules triage, so no API key or local model
download is needed. On first start the stack:

- waits for Postgres and Redis to become healthy;
- runs the database migration (`migrate`);
- loads 32 demo complaints (`seed`, safe to repeat);
- starts the backend, then the frontend once the backend is healthy.

To use offline Ollama triage instead, set `TRIAGE_PROVIDER=ollama` in `.env`
and run `docker compose up -d --build`; the first run pulls and warms the
configured model into the `ollama_models` volume.

Open **http://localhost** for the app. The API docs are at
http://localhost/docs, and http://localhost/ready reports whether Postgres and
Redis are reachable through the frontend proxy.
`docker compose ps -a` should show `migrate` and `seed` as `Exited (0)`, with
`frontend`, `backend`, `postgres` and `redis` healthy. If you enabled Ollama,
`ollama-pull` should also show `Exited (0)`.

| Service | Network | Notes |
| --- | --- | --- |
| `frontend` | edge | nginx (non-root), the only service reachable from the host in prod; port 80 |
| `backend` | edge + internal + llm | exposed only to the frontend proxy on port 8000 |
| `postgres` | internal | volume `pgdata`; no published port |
| `redis` | internal | volume `redisdata`, AOF persistence; no published port |
| `ollama` | llm + models | volume `ollama_models`; `models` only lets it download weights |
| `migrate`, `seed` | internal | one-shot jobs, exit 0 |
| `ollama-pull` | llm | one-shot job, exit 0 |

`internal` and `llm` are both `internal: true`: neither has a route to the
internet, and nothing on `edge` (where `frontend` runs) can resolve `postgres`
or `redis` - only `backend`, via `nginx.conf`'s `/api` proxy. `ollama` is kept
off `internal` and given its own `llm` network instead, so a compromised ollama
container (a third-party image that pulls model weights from the open internet)
has no path to the database or cache - only to `backend`.

Everyday commands:

```powershell
docker compose logs -f backend    # JSON logs, one line per event, with request_id
docker compose down               # stop; all data is kept in the volumes
docker compose down -v            # stop and delete the data
```

In development, `backend/app` is mounted into the container and uvicorn reloads
on save. `compose.prod.yaml` runs the published images by commit SHA instead,
with no mount, no reload and no published database ports:
`IMAGE_TAG=<sha> docker compose -f compose.prod.yaml up -d`.

If you reuse this repo's `.env` for that command, note that `TRIAGE_PROVIDER`
is deliberately *not* read by `compose.prod.yaml` - set `PROD_TRIAGE_PROVIDER`
in your deploy environment instead (defaults to `llm`); see `.env.example`.

## Run without Docker for the app (manual setup)

Useful for debugging the backend in your editor. The databases still run in containers.

| Service | Runs as | Address |
| --- | --- | --- |
| PostgreSQL 16 | Docker container `civicpulse-dev-pg` | `localhost:5432` |
| Redis 7 | Docker container `civicpulse-dev-redis` | `localhost:6379` |
| Ollama (optional) | Docker container `civicpulse-dev-ollama` | `localhost:11434` |
| Backend | `uvicorn` in `backend/.venv` | http://localhost:8000 (API docs at `/docs`) |
| Frontend | Vite dev server | http://localhost:5173 |

**Prerequisites:** Docker Desktop (running), Python 3.12, Node.js 22.
Commands are for PowerShell from the repository root; macOS/Linux differences are noted.

### 1. Start the containers (first time)

```powershell
docker run -d --name civicpulse-dev-pg `
  -e POSTGRES_USER=civicpulse -e POSTGRES_PASSWORD=change_me -e POSTGRES_DB=civicpulse `
  -p 5432:5432 postgres:16-alpine

docker run -d --name civicpulse-dev-redis -p 6379:6379 redis:7-alpine
```

**Optional: Ollama, the fully offline triage provider.** No API key and no data
leaves your machine, but it is slower and less accurate than Groq.

```powershell
docker run -d --name civicpulse-dev-ollama -p 11434:11434 `
  -v civicpulse-dev-ollama-models:/root/.ollama ollama/ollama:0.5.7

docker exec civicpulse-dev-ollama ollama pull llama3.2:1b   # ~1.3 GB, downloaded once into the volume
```

On macOS/Linux, replace the backtick line continuations with `\`.

### 2. Configure

```powershell
Copy-Item .env.example .env        # macOS/Linux: cp .env.example .env
```

The defaults already point at the containers above (`localhost`). Then choose
how complaints are triaged with `TRIAGE_PROVIDER` in `.env`:

| `TRIAGE_PROVIDER` | Needs | Notes |
| --- | --- | --- |
| `rules` (default) | nothing | Keyword rules. Works out of the box |
| `llm` | `GROQ_API_KEY` (free at https://console.groq.com) | Groq `openai/gpt-oss-20b`, ~1 s per complaint |
| `ollama` | the Ollama container above | `llama3.2:1b` on CPU: ~2 s per complaint, first call ~7 s while the model loads |
| `simulated` | nothing | Deterministic fake used by the tests |

Whatever you pick, any failure (timeout, rate limit, bad output, Ollama not
running) falls back to the rules and is recorded as `rules:fallback`: a
complaint is never rejected because the AI is unavailable.

`.env` is gitignored. Never commit it; add new variables to `.env.example`
with placeholder values instead.

### 3. Backend

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1       # macOS/Linux: source .venv/bin/activate
pip install -e ".[dev]"
alembic upgrade head               # create the schema (never done at app startup)
python -m app.seed                 # 32 demo complaints; safe to run again
python -m uvicorn app.main:app --reload
```

Check it at http://localhost:8000/ready. It should say `{"status": "ready"}`.
Then try the API at http://localhost:8000/docs.

### 4. Frontend

In a second terminal:

```powershell
cd frontend
npm ci
npm run dev
```

Open http://localhost:5173.

### Day to day

The containers keep their data. Next time you only need to start them again,
then run the backend and frontend commands from steps 3 and 4 (skip the setup lines):

```powershell
docker start civicpulse-dev-pg civicpulse-dev-redis civicpulse-dev-ollama
docker stop  civicpulse-dev-pg civicpulse-dev-redis civicpulse-dev-ollama
```

(`docker run` a second time fails with "name already in use". Use `docker start`.)

### Troubleshooting

| Symptom | Cause and fix |
| --- | --- |
| `/ready` → 503 `postgres (...)` or `redis (...)` | That container is not running: `docker start civicpulse-dev-pg civicpulse-dev-redis` |
| `/ready` → 503 `... (gaierror)` | `.env` uses a Docker Compose hostname (`@postgres`, `redis://redis`). For local runs use `localhost` |
| Complaints come back `triaged_by: rules:fallback` | The provider failed: check the WARNING log line (it names the error). Usually a missing `GROQ_API_KEY` or Ollama not running |
| `uvicorn app.main:app` fails with "unexpected extra argument" | Run it as `python -m uvicorn app.main:app --reload` |
| Code changes are not picked up | Restart the backend (Ctrl+C, then run it again). `.env` changes always need a restart |
| Port 8000 or 5173 already in use | Another backend/frontend is still running; stop it first |

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

**Triage:** see the provider table above. Duplicate complaints are served from a
24 h content-hash cache, so nine neighbours reporting the same burst main cost
one inference.

```powershell
curl -X POST http://localhost:8000/api/complaints -H "Content-Type: application/json" `
  -d '{"text": "Burst water main flooding Street 12 since fajr", "location": "G-10/4"}'
```

Every response carries an `X-Request-ID` (yours if you send one). Logs are JSON
on stdout, one line per event, each with that `request_id`.

## Development

From `backend/` with the virtualenv active:

```powershell
ruff check .
mypy app
pytest --cov=app        # tests never call a live LLM
```

From `frontend/`:

```powershell
npm run lint
npm run typecheck
npm run build
```
