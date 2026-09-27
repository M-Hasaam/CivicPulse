# Evidence index

What's in this folder, which rubric line it supports, and what's still missing.
Kept honest on purpose: an empty row here is a to-do, not an oversight to hide.

## A · Collaboration and version control

| Rubric line | Marks | Evidence | Status |
| --- | --- | --- | --- |
| `main` protected: no direct push, PR required, CI required, ≥ 1 approval | 3 | `branch-protection-1.png` (ruleset active, empty bypass list, targets `main`)<br>`branch-protection-2-rules.png` (require PR, require status checks, block force pushes, restrict deletions)<br>`branch-protection-3-required-approvals.png` (Required approvals: **1**) | 🟡 Partial — required **status checks list** still empty (screenshot pending `ci.yml`) |
| One deliberate merge conflict, resolved, with markers/resolution/merge evidence and 2–4 sentences on why that version won | 3 | `merge-conflict-1..3-markers-*.png` (conflict markers in `.env.example`, `pyproject.toml`, `config.py`)<br>`merge-conflict-4-resolved-config.png`<br>`merge-conflict-5-merge-commit.png`<br>`MERGE-CONFLICT.md` (what conflicted, reproducible `git log`/`git diff-tree` output, why the resolution won) | ✅ Complete |

## G · Docker and Compose

| Rubric line | Marks | Evidence | Status |
| --- | --- | --- | --- |
| Full Compose stack runs from one command | (supports Docker/Compose demo and README proof) | `compose-stack-healthy.png` (`frontend`, `backend`, `postgres`, `redis`, `ollama` healthy; `migrate`, `seed`, `ollama-pull` exited 0)<br>`compose-api-stats-200.png` (`GET /api/stats` through the frontend proxy returns 200)<br>`compose-api-complaints-200.png` (`GET /api/complaints` returns seeded data)<br>`compose-api-create-complaint-201.png` (`POST /api/complaints` creates a row through the Compose stack)<br>`compose-ollama-model-list.png` (`llama3.2:1b` loaded in Ollama) | ✅ Screenshot evidence captured; still include the live run in the final demo video |
| Frontend provably cannot reach the database | 4 | `compose-frontend-cannot-reach-postgres.png` (`docker compose exec frontend wget -T 3 -O- http://postgres:5432` fails with `bad address`)<br>Also verified live earlier via `docker run --network civicpulse_edge ... nc -z postgres 5432` (fails to resolve) — see the commit messages on `feature/docker-backend` (PRs #25, #28) | 🟡 Screenshot captured — still record this in the **video** demo because the brief asks for a live demonstration |
| `.dockerignore` context sizes before/after | 2 | Reported in the `build(backend): multi-stage non-root Dockerfile` commit message (184.2 MB → 128 kB) | 🟡 In a commit message, not this folder — fine as-is unless the write-up wants it duplicated here |

## D · Data layer

| Rubric line | Marks | Evidence | Status |
| --- | --- | --- | --- |
| `docker compose down` / `up` preserves every row; same for deleting the Postgres pod on K8s | (persistence contract, "you will demonstrate both") | `compose-api-create-complaint-201.png` proves a row can be created through the running Compose stack<br>Verified live multiple times earlier (a complaint survives `down`/`up`; seed reports "already present" on rerun) — see commit messages | ⚪ Compose persistence still belongs in the **video** demo; the K8s-pod-deletion half can't be shown until `feature/k8s` exists |

## H · Kubernetes

| Rubric line | Marks | Evidence | Status |
| --- | --- | --- | --- |
| `kubectl get hpa -w` capture + replicas-vs-load chart | 4 | — | 🔴 Not started — needs `feature/k8s` and a load test |
| VPA recommendations committed, requests updated in response | 3 | — | 🔴 Not started — needs `feature/k8s` |

## I · CI/CD

| Rubric line | Marks | Evidence | Status |
| --- | --- | --- | --- |
| Evidence of a red pipeline blocking a merge, then green | 1 | — | 🔴 Not started — needs `ci.yml` (Burhan's `feature/ci`) and a PR with a deliberately failing test |

## J · Documentation

| Rubric line | Marks | Evidence | Status |
| --- | --- | --- | --- |
| README screenshots | (part of README's 4) | `readme-frontend-ui.png` (frontend loaded at `http://localhost/`)<br>`compose-stack-healthy.png` (Compose services healthy/exited 0)<br>`compose-api-stats-200.png` and `compose-api-complaints-200.png` (API examples for README/run proof) | 🟡 Started — add final README screenshots after CI/CD and K8s are present |
| Demo video ≤ 5 min, both partners speaking | 3 | — | 🔴 Not started — the last thing to record, once Compose, K8s and CI/CD all work |

## Legend
✅ complete · 🟡 partial · ⚪ verified but intentionally not a screenshot (belongs in the video) · 🔴 not started

## Adding new evidence
Each item gets its own small branch + Issue + PR into `dev`, same as everything else in this repo — see `COMMIT-PLAN.md` (on the `team-plan` branch) for the workflow. Update this file's table in the same PR that adds the screenshot.
