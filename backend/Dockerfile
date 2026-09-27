# syntax=docker/dockerfile:1

# Base pinned by digest: the same bytes on every laptop and CI runner.
# python:3.12-slim (Python 3.12.14)
ARG PYTHON_IMAGE=python:3.12-slim@sha256:f77ac9e44ae96ef2c90b8053ea08c31f8be030f824196b0ae4db6d462c84e51f

# --- builder: resolve and install dependencies into a self-contained venv -----------
FROM ${PYTHON_IMAGE} AS builder

ENV PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

RUN python -m venv /opt/venv
ENV PATH=/opt/venv/bin:$PATH

WORKDIR /build
# Dependencies first: this layer is rebuilt only when pyproject.toml changes, not on
# every source edit. A placeholder package satisfies setuptools, then is removed so
# only the third-party dependencies stay in the venv.
COPY pyproject.toml ./
RUN mkdir app && touch app/__init__.py \
    && pip install . \
    && pip uninstall --yes civicpulse-backend

# --- runtime: just the venv and the application --------------------------------------
FROM ${PYTHON_IMAGE}

ENV PATH=/opt/venv/bin:$PATH \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN groupadd --system app && useradd --system --gid app --no-create-home app

WORKDIR /app
COPY --from=builder /opt/venv /opt/venv
COPY alembic.ini ./
COPY alembic ./alembic
COPY app ./app

USER app
EXPOSE 8000

# Liveness only: /health never touches Postgres or Redis
HEALTHCHECK --interval=10s --timeout=3s --start-period=15s --retries=3 \
    CMD ["python", "-c", "import sys, urllib.request; sys.exit(urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=2).status != 200)"]

# Exec form: uvicorn is PID 1 and receives SIGTERM directly. On SIGTERM it stops
# accepting connections, lets in-flight requests finish for up to 20s, then the
# app lifespan closes the HTTP, Redis and database pools.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--timeout-graceful-shutdown", "20"]
