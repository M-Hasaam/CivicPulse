# ADR 0002: Frontend never bakes in a backend URL — nginx proxies /api instead

## Status
Accepted

## Context

A Vite build inlines every `import.meta.env.VITE_*` value into static JavaScript at build
time. If the backend's URL were one of those values, the resulting image would only work
against that one backend — rebuilding per environment, which is exactly the
build-once-deploy-many guarantee the rest of this project depends on (see ADR 0003). The
brief gives two ways out: generate a `/config.js` from environment variables at container
start, or have the frontend's own web server proxy `/api` so the browser never needs an
absolute backend URL at all.

## Decision

We took the proxy route, not the generated-config route. The frontend image is
`nginxinc/nginx-unprivileged` serving the Vite build (`frontend/Dockerfile:20-32`), configured
by one static `nginx.conf` baked into the image (`frontend/Dockerfile:29`,
`frontend/nginx.conf`):

- `location /api/ { proxy_pass http://backend:8000; ... }` (`nginx.conf:12-19`) — every
  backend call the SPA makes goes to same-origin `/api/...`, which nginx forwards to the
  `backend` service on whatever network it's running on.
- `location ~ ^/(docs|openapi\.json|health|ready|metrics)$` (`nginx.conf:21-27`) proxies the
  same way for the OpenAPI schema and observability endpoints.
- The API client itself never constructs an absolute URL: `baseUrl = window.location.origin`
  (`frontend/src/api/client.ts:26-36`) — same-origin, always.

The one thing this depends on is the name `backend` resolving on whatever platform the image
runs on. It does, by construction, on both platforms this project deploys to:
- Docker Compose: the service is literally named `backend` (`compose.yaml:62`), and Compose's
  embedded DNS resolves service names within a network.
- Kubernetes: `k8s/base/backend.yaml` declares a `Service` named `backend` in the `civicpulse`
  namespace, and cluster DNS resolves a Service name the same way inside that namespace. The
  Ingress (`k8s/base/ingress.yaml`) only needs one rule, `/ → frontend` — it doesn't need a
  second `/api → backend` rule, because the frontend pod's own nginx (same image, same
  `nginx.conf`) already does that proxying internally, identically to how it works in Compose.

No `VITE_API_URL`, no build-time backend hostname, anywhere in `frontend/src` — confirmed by
grep; the only per-environment values are `TRIAGE_PROVIDER`, credentials, etc., which live in
the *backend's* environment/K8s Secret, never in a value the browser receives.

## Consequences

- The exact same frontend image — `ghcr.io/.../frontend:<sha>` — runs unmodified against
  Compose locally, the ephemeral CI kind cluster, and a future real deployment. Nothing about
  the image is environment-specific.
- The frontend can never be pointed at a *different* backend than the one on its own network
  without rebuilding — that's the whole point, and also means there's no runtime knob to
  redirect API traffic if that were ever needed (e.g. a canary backend). A generated
  `/config.js` would allow that; this design trades that flexibility for a single static
  file and one less moving part.
- This only works because the frontend and backend are always deployed together, on
  networks where `backend` resolves. That's true for this project's two targets; it would
  not be true if the frontend were ever served from a separate origin (e.g. a CDN) without
  its own reverse proxy in front of it.
