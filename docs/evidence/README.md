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
| Frontend provably cannot reach the database | 4 | Verified live, repeatedly, via `docker run --network civicpulse_edge ... nc -z postgres 5432` (fails to resolve) — see the commit messages on `feature/docker-backend` (PRs #25, #28) | ⚪ Not screenshotted — the brief asks for this as a **video** demo (`docker compose exec frontend ping postgres` failing on camera), not a static file here |
| `.dockerignore` context sizes before/after | 2 | Reported in the `build(backend): multi-stage non-root Dockerfile` commit message (184.2 MB → 128 kB) | 🟡 In a commit message, not this folder — fine as-is unless the write-up wants it duplicated here |

## D · Data layer

| Rubric line | Marks | Evidence | Status |
| --- | --- | --- | --- |
| `docker compose down` / `up` preserves every row; same for deleting the Postgres pod on K8s | (persistence contract, "you will demonstrate both") | Verified live multiple times (a complaint survives `down`/`up`; seed reports "already present" on rerun) — see commit messages | ⚪ Not screenshotted — also a **video** demo item; the K8s-pod-deletion half can't be shown until `feature/k8s` exists |

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
| README screenshots | (part of README's 4) | — | 🔴 Not started |
| Demo video ≤ 5 min, both partners speaking | 3 | — | 🔴 Not started — the last thing to record, once Compose, K8s and CI/CD all work |

## Legend
✅ complete · 🟡 partial · ⚪ verified but intentionally not a screenshot (belongs in the video) · 🔴 not started

## Adding new evidence
Each item gets its own small branch + Issue + PR into `dev`, same as everything else in this repo — see `COMMIT-PLAN.md` (on the `team-plan` branch) for the workflow. Update this file's table in the same PR that adds the screenshot.
