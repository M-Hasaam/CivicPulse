# ADR 0003: Deploy by immutable commit SHA — `:latest` is pushed, never deployed

## Status
Accepted

## Context

"What is production running?" needs a one-word answer you can paste into `git show`. A
`:latest` tag is a moving pointer: two people asking "what's deployed?" five minutes apart
could get two different answers to the same tag, and there is no way to `git show` a moving
pointer. The brief calls this out as a non-negotiable and an automatic −8 if violated
("Deploying `:latest` anywhere").

## Decision

`cd.yml`'s `publish-and-deploy` job builds and pushes **two** tags per image —
`:${{ steps.meta.outputs.sha }}` and `:latest` (`.github/workflows/cd.yml:80-81, 89-90`) —
but only the SHA tag is ever deployed. The "Deploy SHA-tagged images" step
(`cd.yml:130-141`) renders the base manifests with Kustomize, then uses
`kubectl set image --local` to overwrite the image reference for `backend`, `migrate`, and
`frontend` with that exact commit's SHA tag (`cd.yml:131-137`) before ever calling
`kubectl apply` (`cd.yml:138`). The `:latest` tag exists only so a human can `docker pull` the
newest image by name for a quick manual check — it is never what a cluster runs.

`:latest` is genuinely useful for something else: `k8s/base/kustomization.yaml`'s own
`images:` block defaults to `newTag: dev` (and the prod overlay to `newTag: latest`) purely
as a placeholder so `kubectl apply -k k8s/base` works standalone during local development
without CI's SHA substitution. Every real deploy path (`cd.yml`) overrides it.

`release.yml` reinforces the same rule from the other direction: on a `v*` tag push it builds
and pushes semver tags (`:v1.2.3`), gated on `quality-gate` (the full `ci.yml` suite) passing
first (`release.yml`, `needs: quality-gate`) — so a permanent version tag can never be
attached to an image that never passed lint/type-check/tests.

## Consequences

- `git show <the-sha-tag>` is always a complete, truthful answer to "what's running,"
  because the tag *is* the commit.
- Rollback has an exact target: re-render the manifests with the previous good commit's SHA
  and re-apply (see `docs/RUNBOOK.md`'s declarative rollback path), rather than guessing at
  what `:latest` pointed to an hour ago.
- The cost: every deploy needs the orchestration in `cd.yml:130-141` (render → substitute →
  apply) rather than a bare `kubectl apply -k`. That's a few extra lines in one workflow file,
  paid once, for a guarantee that holds everywhere else.
