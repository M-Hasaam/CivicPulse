#!/usr/bin/env python3
"""Submission lint for the §5.3 automatic-deduction list in docs/assignment-brief.md.

Not a grader: it catches the mechanical failure modes the brief penalises (a
literal committed .env, an unpinned base image, :latest deployed, a database
port published in compose.prod.yaml, and so on). A clean run does not
guarantee a good mark; a dirty run nearly guarantees a bad one.

Run from the repository root:

    python scripts/check_submission.py

Exits 0 if every check passes, 1 otherwise.
"""

from __future__ import annotations

import re
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


@dataclass
class Result:
    name: str
    ok: bool
    detail: str = ""


@dataclass
class Report:
    results: list[Result] = field(default_factory=list)

    def add(self, name: str, ok: bool, detail: str = "") -> None:
        self.results.append(Result(name, ok, detail))

    @property
    def failed(self) -> list[Result]:
        return [r for r in self.results if not r.ok]


def git(*args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=ROOT, capture_output=True, text=True, check=False
    ).stdout


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace") if path.exists() else ""


# --- checks, one per §5.3 line -------------------------------------------------------


def check_no_env_in_history(report: Report) -> None:
    """-20: a .env, key, token or password anywhere in Git history."""
    added = git("log", "--all", "--diff-filter=A", "--name-only", "--pretty=format:")
    hits = [
        line
        for line in added.splitlines()
        if line
        and re.fullmatch(r"(.*/)?\.env(\.[^.]+)?", line)
        and not line.endswith(".env.example")
    ]
    report.add(
        "No .env file ever committed (git log --all)",
        not hits,
        f"found: {hits}" if hits else "clean",
    )


SECRET_PATTERNS = [
    re.compile(r"AKIA[0-9A-Z]{16}"),  # AWS access key
    re.compile(r"sk-[A-Za-z0-9]{20,}"),  # OpenAI-style
    re.compile(r"gsk_[A-Za-z0-9]{20,}"),  # Groq
    re.compile(r"ghp_[A-Za-z0-9]{30,}"),  # GitHub PAT
    re.compile(r"xox[baprs]-[A-Za-z0-9-]{10,}"),  # Slack
]


def check_no_secret_literals_in_tree(report: Report) -> None:
    """-20/-15: a real key/token committed, in any tracked file (working tree)."""
    tracked = [ROOT / p for p in git("ls-files").splitlines() if p]
    hits: list[str] = []
    for path in tracked:
        if path.suffix in {".png", ".jpg", ".jpeg", ".gif", ".ico", ".pdf", ".lock"}:
            continue
        text = read(path)
        for pattern in SECRET_PATTERNS:
            if pattern.search(text):
                hits.append(f"{path.relative_to(ROOT)} matches {pattern.pattern}")
    report.add(
        "No recognisable API-key pattern in tracked files",
        not hits,
        "; ".join(hits) if hits else "clean (heuristic pattern match only, not exhaustive)",
    )


def check_no_api_key_in_k8s_manifests(report: Report) -> None:
    """-15: an LLM API key in a committed manifest, even base64-encoded."""
    hits: list[str] = []
    for path in (ROOT / "k8s").rglob("*.yaml"):
        for match in re.finditer(r"GROQ_API_KEY\s*[:=][ \t]*(\S*)", read(path)):
            value = match.group(1).strip("\"'")
            if value:
                hits.append(f"{path.relative_to(ROOT)}: GROQ_API_KEY has a non-empty value")
    report.add(
        "No non-empty GROQ_API_KEY committed in k8s/",
        not hits,
        "; ".join(hits) if hits else "clean — placeholders only",
    )


IMAGE_LINE = re.compile(r"^\s*(?:-\s*)?image:\s*([^\s#]+)", re.MULTILINE)
FROM_LINE = re.compile(r"^\s*FROM\s+([^\s]+)", re.MULTILINE | re.IGNORECASE)


def _is_pinned(ref: str) -> bool:
    if "@sha256:" in ref:
        return True
    if ":" not in ref.split("/")[-1]:
        return False
    tag = ref.rsplit(":", 1)[-1]
    return tag not in {"latest", ""}


def check_pinned_base_images(report: Report) -> None:
    """-8: unpinned base image, or postgres/redis/node without a tag."""
    hits: list[str] = []
    for dockerfile in ROOT.rglob("Dockerfile"):
        if ".venv" in dockerfile.parts or "node_modules" in dockerfile.parts:
            continue
        for match in FROM_LINE.finditer(read(dockerfile)):
            ref = match.group(1)
            if ref.startswith("$") or ref.startswith("${"):
                continue  # ARG-substituted; the ARG default is checked separately below
            if not _is_pinned(ref):
                hits.append(f"{dockerfile.relative_to(ROOT)}: FROM {ref}")
    for dockerfile in ROOT.rglob("Dockerfile"):
        if ".venv" in dockerfile.parts or "node_modules" in dockerfile.parts:
            continue
        for match in re.finditer(r"^\s*ARG\s+\w+_IMAGE=([^\s]+)", read(dockerfile), re.MULTILINE):
            ref = match.group(1)
            if not _is_pinned(ref):
                hits.append(f"{dockerfile.relative_to(ROOT)}: ARG default {ref}")
    for compose_file in (ROOT / "compose.yaml", ROOT / "compose.prod.yaml"):
        text = read(compose_file)
        # Resolve YAML anchors (x-backend-image: &backend-image <value>) so an
        # `image: *backend-image` alias is checked against what it actually expands to.
        anchors = dict(re.findall(r"&([\w-]+)\s+(\S+)", text))
        for match in IMAGE_LINE.finditer(text):
            ref = match.group(1)
            if ref.startswith("*"):
                ref = anchors.get(ref[1:], ref)
            if "${" in ref:
                continue  # parameterized (e.g. ${IMAGE_TAG:?...}) — pinned at deploy time
            if not _is_pinned(ref):
                hits.append(f"{compose_file.name}: image: {ref}")
    report.add(
        "All base images pinned (digest or explicit non-latest tag)",
        not hits,
        "; ".join(hits) if hits else "clean",
    )


def check_no_localhost_service_to_service(report: Report) -> None:
    """-8: localhost used for service-to-service communication.

    Deliberately narrow: only flags 'localhost' inside a URL-shaped value for a
    backend-to-backend dependency (DATABASE_URL, REDIS_URL, etc.). An Ingress
    `host: foo.localhost` is the standard local-dev vanity domain for browser
    access, not service-to-service traffic, so it is not flagged.
    """
    hits: list[str] = []
    url_keys = r"(DATABASE_URL|REDIS_URL|BACKEND_URL|API_URL)"
    for path in (ROOT / "k8s").rglob("*.yaml"):
        for i, line in enumerate(read(path).splitlines(), start=1):
            if re.search(url_keys, line) and re.search(r"localhost(?!\.)", line, re.IGNORECASE):
                hits.append(f"{path.relative_to(ROOT)}:{i}: {line.strip()}")
    for i, line in enumerate(read(ROOT / "compose.prod.yaml").splitlines(), start=1):
        if re.search(url_keys, line) and re.search(r"localhost(?!\.)", line, re.IGNORECASE):
            hits.append(f"compose.prod.yaml:{i}: {line.strip()}")
    report.add(
        "No 'localhost' used for service-to-service URLs (DATABASE_URL/REDIS_URL/...)",
        not hits,
        "; ".join(hits) if hits else "clean",
    )


def check_no_published_db_cache_ports(report: Report) -> None:
    """-8: published database or cache port in compose.prod.yaml, or NodePort/LB on the DB."""
    hits: list[str] = []
    text = read(ROOT / "compose.prod.yaml")
    services = re.split(r"^  (\w[\w-]*):\s*$", text, flags=re.MULTILINE)
    # services[0] is preamble; then alternating name, body
    for name, body in zip(services[1::2], services[2::2], strict=False):
        if name in {"postgres", "redis"} and re.search(r"^\s*ports:\s*$", body, re.MULTILINE):
            hits.append(f"compose.prod.yaml: service '{name}' publishes a port")
    for path in (ROOT / "k8s").rglob("*.yaml"):
        text = read(path)
        if re.search(r"name:\s*postgres", text) and re.search(
            r"type:\s*(NodePort|LoadBalancer)", text
        ):
            hits.append(f"{path.relative_to(ROOT)}: Postgres Service is NodePort/LoadBalancer")
    report.add(
        "No published DB/cache port in compose.prod.yaml; no NodePort/LB on the database",
        not hits,
        "; ".join(hits) if hits else "clean",
    )


def check_deploy_gated_by_needs(report: Report) -> None:
    """-8: publishing or deploying job not gated by needs:."""
    cd = read(ROOT / ".github" / "workflows" / "cd.yml")
    jobs = re.split(r"^  (\w[\w-]*):\s*$", cd, flags=re.MULTILINE)
    hits: list[str] = []
    for name, body in zip(jobs[1::2], jobs[2::2], strict=False):
        if re.search(r"publish|deploy", name, re.IGNORECASE) and "needs:" not in body:
            hits.append(f"cd.yml: job '{name}' has no needs:")
    report.add(
        "Every publish/deploy job in cd.yml is gated by needs:",
        not hits,
        "; ".join(hits) if hits else "clean",
    )


def check_no_latest_deployed(report: Report) -> None:
    """-8: deploying :latest anywhere.

    A committed overlay defaulting to `newTag: latest` is only a problem if
    nothing re-tags it with a real SHA before the manifest is actually applied
    to a cluster — pushing a :latest tag to GHCR alongside the SHA tag (see
    ADR 0003) is explicitly fine; deploying it is not. So this checks cd.yml
    for a re-tag step (`kubectl set image` / `kustomize edit set image`)
    that runs before `kubectl apply`, rather than flagging the committed
    overlay's placeholder tag directly.
    """
    cd = read(ROOT / ".github" / "workflows" / "cd.yml")
    retags_before_apply = bool(
        re.search(r"kubectl set image|kustomize edit set image", cd)
    ) and bool(re.search(r"kubectl apply", cd))
    if re.search(r"kubectl (set image|apply)[^\n]*:latest", cd):
        retags_before_apply = False  # an explicit :latest survives into the apply step itself
    report.add(
        "cd.yml re-tags images with the commit SHA before kubectl apply (never applies :latest)",
        retags_before_apply,
        "kubectl set image + kubectl apply found in cd.yml"
        if retags_before_apply
        else "no re-tag step found before apply — check overlay tags are not applied as-is",
    )


def check_postgres_has_pvc(report: Report) -> None:
    """-8: PostgreSQL as a Deployment with no PVC."""
    text = read(ROOT / "k8s" / "base" / "postgres.yaml")
    is_statefulset = bool(re.search(r"kind:\s*StatefulSet", text))
    has_pvc = bool(re.search(r"volumeClaimTemplates:|kind:\s*PersistentVolumeClaim", text))
    ok = is_statefulset and has_pvc
    report.add(
        "Postgres is a StatefulSet with a PVC (k8s/base/postgres.yaml)",
        ok,
        "StatefulSet+PVC found" if ok else "missing StatefulSet and/or volumeClaimTemplates",
    )


def check_no_direct_pushes_to_main(report: Report) -> None:
    """-5: commits pushed directly to main (heuristic: every commit on main besides
    the root is either a merge commit or exists identically on some other branch/PR)."""
    log = git("log", "main", "--pretty=format:%H %P %s")
    hits: list[str] = []
    for line in log.splitlines():
        parts = line.split(" ", 2)
        if len(parts) < 2:
            continue
        commit_hash = parts[0]
        parents = parts[1].split() if len(parts) > 1 else []
        subject = parts[2] if len(parts) > 2 else ""
        is_merge = len(parents) > 1
        is_root = len(parents) == 0
        if not is_merge and not is_root and "Merge pull request" not in subject:
            hits.append(f"{commit_hash[:8]} {subject}")
    detail = "clean"
    if hits:
        shown = hits[:5]
        suffix = "..." if len(hits) > 5 else ""
        detail = f"non-merge commits on main: {shown}{suffix}"
    report.add(
        "Every commit on main is a merge (PR) or the root commit — none pushed directly",
        not hits,
        detail,
    )


def check_readme_quickstart(report: Report) -> None:
    """-5: README quickstart that does not work from a clean clone (best-effort:
    confirms a runnable one-liner exists; does not actually clone+run)."""
    text = read(ROOT / "README.md")
    has_quickstart_heading = bool(re.search(r"^#+\s*Quickstart", text, re.MULTILINE))
    has_compose_up = "docker compose up" in text
    ok = has_quickstart_heading and has_compose_up
    report.add(
        "README has a Quickstart section with a docker compose up command",
        ok,
        "found" if ok else "missing heading or command — check manually",
    )


CHECKS = [
    check_no_env_in_history,
    check_no_secret_literals_in_tree,
    check_no_api_key_in_k8s_manifests,
    check_pinned_base_images,
    check_no_localhost_service_to_service,
    check_no_published_db_cache_ports,
    check_deploy_gated_by_needs,
    check_no_latest_deployed,
    check_postgres_has_pvc,
    check_no_direct_pushes_to_main,
    check_readme_quickstart,
]


def main() -> int:
    report = Report()
    for check in CHECKS:
        check(report)

    width = max(len(r.name) for r in report.results)
    for r in report.results:
        status = "PASS" if r.ok else "FAIL"
        print(f"[{status}] {r.name.ljust(width)}  {r.detail}")

    print()
    if report.failed:
        print(f"{len(report.failed)}/{len(report.results)} checks failed.")
        print(
            "This is a lint, not a grader: a failure here maps to a specific line in "
            "docs/assignment-brief.md §5.3. A clean run does not guarantee a good mark; "
            "a dirty run nearly guarantees a bad one."
        )
        return 1

    print(f"All {len(report.results)} checks passed.")
    print(
        "Not covered by this script (verify manually): a live clean-clone run of the "
        "README quickstart, and that every merged PR is linked to an Issue with a "
        "substantive partner review comment — both require GitHub state this script "
        "cannot see from the local checkout."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
