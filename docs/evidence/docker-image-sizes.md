# Docker build-context and image sizes

Brief requirement (§2, Docker layer): ".dockerignore in each build context — report build-context
size before and after, with numbers" and "report both stage sizes; a frontend image over ~60 MB
means the multi-stage split is not doing its job."

Measured with `DOCKER_BUILDKIT=1 docker build --no-cache --progress=plain`, reading BuildKit's own
`transferring context: …` line, which is the exact byte count sent from the Docker client to the
daemon before any layer is built.

## Backend

Historical measurement, taken when `.dockerignore` was introduced (`a59a2e1`, "build(backend):
multi-stage non-root Dockerfile and .dockerignore"), with a populated `.venv`, `__pycache__`,
`.mypy_cache`, `.ruff_cache` and `htmlcov` present locally at the time:

| | Context size | Final image |
| --- | --- | --- |
| Before `.dockerignore` | 184.2 MB | — |
| After `.dockerignore` | 128 kB | 324 MB |

Re-verified today (2026-09-28) from a clean worktree with none of those caches present, so the
context is smaller still — 97.03 kB — confirming the `.dockerignore` entries for `.venv`,
`__pycache__`, `.mypy_cache`, `.ruff_cache`, `.pytest_cache`, `.coverage`, `htmlcov` and `tests` are
doing real work, not just excluding files that were never going to be sent anyway. Final image size
unchanged at 324 MB.

## Frontend

No prior measurement existed for the frontend build context. Measured today (2026-09-28) with
`node_modules` installed locally (`npm ci`, 158 packages) to reproduce a realistic developer
working tree — the scenario `.dockerignore` actually needs to guard against:

| | Context size | Final image |
| --- | --- | --- |
| Before `.dockerignore` | 190.34 MB | — |
| After `.dockerignore` | 1.45 kB | 112 MB |

The ~190 MB → ~1.5 kB drop is almost entirely `node_modules` (not shipped; reinstalled inside the
builder stage via `npm ci` against `package-lock.json`), plus `dist`, `coverage`, `.git`-adjacent
files and editor config excluded by `frontend/.dockerignore`.

**Final image size note:** 112 MB is over the brief's ~60 MB guidance for a frontend image. Layer
breakdown (`docker history`) shows this is not a multi-stage leak — the built app itself is 315 kB
(`COPY /build/dist`) plus a 20.5 kB nginx config; the remaining ~111 MB is the
`nginxinc/nginx-unprivileged:1.29-alpine` base image itself, which compiles in extra nginx modules
(`geoip`, `image-filter`, `xslt`, `njs`) plus an `apk upgrade` layer (21.8 MB) for security patches.
The multi-stage split is working correctly (no Node toolchain or `node_modules` reaches the final
image); the base image choice is what drives the total. A slimmer alternative (plain `nginx:alpine`
with a manually-added non-root user, dropping the unused nginx modules) would land under 60 MB, at
the cost of re-adding the non-root setup that `nginx-unprivileged` provides for free. Left as a
documented trade-off rather than changed, since correctness (non-root, no toolchain leakage) was
prioritized over the size guidance.
