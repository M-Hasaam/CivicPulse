# Runbook

Operational reference: how to deploy, how to roll back, how to read logs, and what to do
when triage starts failing. Written for whoever's on call, including future-you at 3am.

## Deploying

Deploys happen automatically on push to `main`, via `.github/workflows/cd.yml`:

1. `quality-gate` (full test suite) and `manifests` (Kustomize + kubeconform) both have to
   pass before anything publishes — gated by `needs: [quality-gate, manifests]`
   (`cd.yml:39-42`).
2. `publish-and-deploy` builds and pushes both images to GHCR, tagged with the commit SHA
   *and* `latest` (`cd.yml:68-90`) — see `docs/adr/0003-deploy-by-sha.md` for why only the
   SHA tag is ever actually deployed.
3. A kind cluster is created, nginx-ingress and metrics-server are installed, the `ghcr-pull`
   image secret is created, then the manifests are rendered and re-tagged with that exact SHA
   (`cd.yml:130-137`) before `kubectl apply` (`cd.yml:138`).
4. The job waits on the migrate `Job` completing, then on both Deployments' `rollout status`
   (`cd.yml:139-141`), then smoke-tests the Ingress (`cd.yml:143-149`) and confirms the HPA is
   reading live metrics (`cd.yml:151-163`) before declaring success.

**Manual/local deploy** (e.g. for the HPA/VPA load-test session): `kubectl apply -k
k8s/overlays/prod` against a cluster you've already pointed `kubectl` at, after copying
`k8s/overlays/prod/secrets.env.example` to `k8s/overlays/prod/secrets.env` (gitignored) with a
real password.

## Rolling back

Two mechanisms, for two different situations:

**Fast, imperative — the 3am answer.** Something just broke after a rollout and you need the
previous version back *now*:

```
kubectl rollout undo deployment/backend -n civicpulse
kubectl rollout undo deployment/frontend -n civicpulse
```

This reverts to the Deployment's previous `ReplicaSet` — fast, but leaves the cluster in a
state that doesn't match any commit in the repo, and the next `cd.yml` run on `main` will
push it right back to whatever's newest. Use this to stop the bleeding, not as the fix.

**Declarative, auditable — the correct answer once the fire is out.** Re-apply the previous
known-good commit's SHA, the same way `cd.yml` deploys any commit:

```
git rev-parse HEAD~1   # or whichever commit was last known-good
kubectl kustomize k8s/overlays/prod > rendered-prod.yaml
kubectl set image --local -f rendered-prod.yaml \
  backend=ghcr.io/m-hasaam/civicpulse/backend:<that-sha> \
  migrate=ghcr.io/m-hasaam/civicpulse/backend:<that-sha> \
  frontend=ghcr.io/m-hasaam/civicpulse/frontend:<that-sha> \
  -o yaml > rendered-prod-sha.yaml
kubectl apply -f rendered-prod-sha.yaml
```

This is what actually belongs in git history and in an incident writeup — `git show <sha>`
always names exactly what's running, per ADR 0003.

## Reading logs

Every backend log line is one JSON object to stdout (`app/logging_config.py`), carrying a
`request_id` propagated from the `X-Request-ID` header or generated if absent
(`app/main.py:54-58`, `logging_config.py`). Never look for a log file inside a container —
the filesystem is ephemeral by design.

```
kubectl logs -n civicpulse -l app.kubernetes.io/name=backend --tail=200 -f
kubectl logs -n civicpulse -l app.kubernetes.io/name=frontend --tail=200 -f
docker compose logs -f backend      # Compose equivalent
```

Grep for a specific request across services: every access-log line and every triage
fallback warning carries the same `request_id`, so `... | grep '"request_id": "<id>"'`
reconstructs one request's full path through the system.

## When triage starts failing

"Failing" for triage never means a 500 to the citizen — `TriageOrchestrator` always falls
back to `RuleBasedTriage` on any provider error (`app/services/triage_service.py:90-104`).
What "failing" means operationally is the *fallback rate* climbing. Diagnose in this order:

1. **`GET /api/meta/providers`** — shows which provider is configured (`settings.TRIAGE_PROVIDER`)
   and the last 20 triage outcomes: provider, latency, and whether each one fell back
   (`app/routes/stats.py:16-18`, backed by `app/cache/triage_log.py`). Start here — it's the
   system's own observability surface for exactly this question.
2. **`/metrics`** — `TRIAGE_FALLBACKS{provider=...,error=...}` (a counter, incremented in
   `triage_service.py:95`) tells you *what kind* of failure is happening: `TimeoutError` means
   the provider is slow (check the 10s `TRIAGE_TIMEOUT_SECONDS` budget and Groq's own status
   page); `TriageUnavailableError` after a `429`/`5xx` means you're being rate-limited or the
   upstream is down; `InvalidTriageOutputError` means the model is returning malformed JSON
   (a prompt/model-version regression, not an outage).
3. **Logs**: each fallback logs one `WARNING` line with the complaint id, provider, and error
   class (`triage_service.py:110-113` via the shared `logger.warning` in `http.py`) — `kubectl
   logs ... | grep '"level": "WARNING"'` finds every one.
4. **`/ready`** (`app/routes/health.py:20-41`) — confirms this isn't actually a Postgres/Redis
   outage masquerading as a triage problem; it names the failed dependency explicitly if so.
5. **Mitigate**: if the hosted provider is genuinely down or rate-limited for a while, set
   `TRIAGE_PROVIDER=rules` (or `ollama`, if that stack is running) via the `civicpulse-config`
   ConfigMap and roll the backend Deployment — citizens keep getting triaged, just without the
   LLM's judgment, until the provider recovers.

## Health vs. readiness, for whoever's confused by a restart loop

- `/health` (liveness) never touches Postgres or Redis (`health.py:11-17`) — a slow database
  must never restart every backend pod.
- `/ready` (readiness) checks both and returns 503 naming which one failed (`health.py:20-41`)
  — this is what removes a pod from the Service, not what restarts it.
- If pods are restart-looping on startup, check `startupProbe` first
  (`k8s/base/backend.yaml`) — it exists precisely to give a slow boot up to 60s
  (`failureThreshold: 30 × periodSeconds: 2`) before liveness even starts counting failures.
