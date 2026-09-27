# Engineering notes

Answers to the eight questions in the assignment brief §5.2, with references to this repo's
own files and lines. Five are answered below from what's already built and verified. Three
(marked 🔴) genuinely can't be answered honestly from the repo alone — they need either a
lecture reference, real load-test data, or an actual remembered incident, and are left as
open TODOs rather than invented, per this project's own evidence policy (see
`docs/evidence/README.md`: "an empty row here is a to-do, not an oversight to hide").

## 1. Three things that differ between a laptop and a CI runner, and the exact line that freezes each

- **Base image bytes.** A tag like `python:3.12-slim` can resolve to different underlying
  bytes on different days as upstream pushes patches. Frozen by pinning the digest, not the
  tag: `backend/Dockerfile:5` (`python:3.12-slim@sha256:f77ac9e4...`) and
  `frontend/Dockerfile:4-5` (both the Node builder and the nginx runtime image). A laptop
  building today and a CI runner building next month get the identical image.
- **Frontend dependency resolution.** `npm install` re-resolves the dependency tree against
  whatever the registry currently has that satisfies the ranges in `package.json` — a laptop
  and a CI runner running it a week apart can silently get different transitive versions.
  Frozen by `frontend/Dockerfile:14-15`: `COPY package.json package-lock.json ./` then
  `RUN npm ci` (not `npm install`) — `npm ci` fails outright on any lockfile mismatch instead
  of re-resolving, so the exact tree in `package-lock.json` is what gets installed, everywhere.
- **Clock/timezone.** A laptop's local timezone and a CI runner's (usually UTC, but not
  guaranteed) differ. Frozen by never relying on naive local time: the schema uses
  `timestamptz` throughout (`backend/app/repositories/models.py`), and application code calls
  `datetime.now(UTC)` explicitly (e.g. `app/services/triage_service.py:64`), so a timestamp
  means the same instant regardless of which machine's clock produced it.

**Not yet frozen, worth stating honestly:** backend Python dependencies are declared with
`>=` ranges and no lock file (`backend/pyproject.toml:6-16`) — unlike the frontend, a
`pip install .` on a laptop today and on a CI runner in a month are *not* guaranteed to
resolve to the same versions. This is a real gap, not an oversight we're hiding: pinning
would mean adding a lock step (e.g. `pip-compile` or switching to `uv`/Poetry with a
committed lock file).

## 2. CI/CD maturity ladder rung 🔴 needs Lecture 03 slide 32

Not answerable from the repo alone — this question asks us to place the pipeline on a
specific named ladder from a lecture slide we don't have the exact rung names for. **TODO:**
whoever has the slide, fill in: which rung `ci.yml` + `cd.yml` + `release.yml` currently sit
on, justify it against what's actually built here (lint/test/build/scan/manifest-validate on
every PR; test→build→push→deploy→smoke-test on `main`; semver release gated on the same
suite; branch protection with required status checks), name the next rung up, and what it
would buy (candidates worth considering once the slide is in hand: progressive/canary
delivery, automated rollback on a failed post-deploy health check, GitOps reconciliation —
see the bonus section for related ideas already scoped out).

## 3. The exact line guaranteeing build-once-deploy-many, and what breaks without it

`.github/workflows/cd.yml:130-137` — after rendering the base manifests once, it substitutes
the image reference for `backend`, `migrate`, and `frontend` with `${{ steps.meta.outputs.sha
}}` via `kubectl set image --local`, *before* the one `kubectl apply` (`cd.yml:138`) that
deploys them. The image itself was built exactly once, earlier in the same job
(`cd.yml:68-90`); this step only ever re-labels which already-built image a manifest points
at. See `docs/adr/0003-deploy-by-sha.md` for the full decision.

Without this: either every environment needs its own image build (defeating "build once"
outright), or manifests reference a moving tag like `:latest`, and "what's deployed" stops
having a single, git-showable answer — two people checking five minutes apart could see two
different realities behind the same tag.

## 4. What "correct" means for a probabilistic component, and how CI stayed deterministic

With `TRIAGE_PROVIDER=llm`, the *judgment* (which category a given complaint gets) is not
deterministic — the same complaint could plausibly get "roads" from one call and "other" from
another. "Correct" for this component was redefined away from "the model picked the
objectively right category" (unfalsifiable, and not something a test can assert) to
**"the system's behavior around the model is deterministic even when the model's output
isn't"**: every output is schema-validated before anything else sees it
(`providers/triage/base.py:53-65`), a failure of any kind falls back the same way every time
(`services/triage_service.py:90-104`, always `triaged_by="rules:fallback"`), and the one test
that touches adversarial model behavior — `test_prompt_injection_cannot_choose_the_category`
(`backend/tests/test_api.py:136-164`) — deliberately does not assert *which* category comes
back; it asserts that the category is one your schema allows, decided by validation, not by
text an attacker controlled.

CI itself stays fully deterministic by never calling a real model at all:
`TRIAGE_PROVIDER=simulated` (`.github/workflows/ci.yml:26`) selects `SimulatedTriage`
(`providers/triage/simulated.py`), a seeded fake with injectable failure — so the test suite's
pass/fail is a function of the code, never of what a hosted model answers on a given run.

## 5. HPA lag 🔴 needs the local load-test capture

Not answerable yet — this needs a real `kubectl get hpa -w` run against a live local cluster
under generated load (k6/hey), which hadn't been executed at the time of writing (the
manifest side — `k8s/base/hpa.yaml`, `pdb.yaml`, `vpa.yaml`, metrics-server install in
`cd.yml` — is built and verified; the load-test session itself is the remaining step). **TODO
once that run happens:** fill in the observed seconds between load rising and `REPLICAS`
rising in the `-w` capture, and attribute the lag across: metrics-server's scrape interval,
the HPA controller's own sync period (default 15s), and pod scheduling + image pull +
`startupProbe` time (`backend.yaml`'s `failureThreshold: 30 × periodSeconds: 2` = up to 60s
grace before a slow-booting pod even counts as live).

## 6. Why VPA runs in `Off` mode, and the Auto-mode conflict with HPA

`k8s/base/vpa.yaml`: `updatePolicy: { updateMode: "Off" }` — recommender only, never evicts a
running pod to resize it. If VPA instead ran in `Auto` mode alongside the CPU-based HPA
(`k8s/base/hpa.yaml`), the two would fight over the same signal: VPA raising a pod's CPU
*request* lowers the HPA's computed utilization (`usage ÷ request`), which makes the HPA
scale *in* (fewer, now-larger pods) — which raises per-pod load again, which makes VPA raise
the request further, which lowers utilization again. Recommender mode plus a human in the
loop (record the `Target`/`Lower Bound`/`Upper Bound` from `kubectl describe vpa backend-vpa`,
then deliberately update `backend.yaml`'s `resources.requests` and re-test) is the standard
resolution — VPA informs a static, reviewed decision instead of continuously fighting the HPA
for control of the same number.

## 7. The `internal: true` network and the hosted LLM

`compose.yaml:180-185` marks both `internal` (Postgres/Redis) and `llm` (Ollama) as
`internal: true` — no route to the outside world. The `backend` service is deliberately *not*
confined to only those: it also joins `edge` (`compose.yaml:92`), a normal (non-internal)
bridge network, and the comment at `compose.yaml:5` states the reason directly: "Normal
bridge, so the backend can also reach Groq." `edge`'s only other member is `frontend`
(`compose.yaml:169`) — so the same network that lets the browser's requests reach the backend
is also, incidentally, the backend's only route to the public internet, since Docker's bridge
driver NATs a non-internal network out by default. Postgres, Redis, and Ollama stay
unreachable from outside precisely because they're never attached to `edge` at all
(`compose.yaml:34,52,118`, `internal`/`llm` only) — the isolation and the egress path are two
independent facts about which networks a service joins, not a single flag to trade off.

## 8. The failure 🔴 needs an actual incident

Not fabricated here — this question asks for something that genuinely cost the team more than
an hour: the symptoms, what was wrongly believed first, and the exact command or log line
that eventually revealed the real cause. **TODO:** whoever hit that incident (the required
status check rename in PR #33/#35 that silently blocked merges is one real candidate already
on record in this session — see the review comments on PR #33 — but there may be a better,
costlier one from earlier in the project worth writing up instead) should fill this in
directly; it needs to be told from memory, not reconstructed from the repo.
