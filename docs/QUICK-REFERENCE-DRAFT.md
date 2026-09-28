# Quick reference draft

Temporary documentation exercise summarizing existing project guidance. This draft is scheduled for removal at the end of the exercise.

## Project overview

Start with the [project README](../README.md) for the architecture diagram, stack, and setup instructions.

## Evidence index

The [evidence index](evidence/README.md) maps captured artifacts to the assignment requirements.

## Operations

Use the [runbook](RUNBOOK.md) for deployment, rollback, log inspection, and triage troubleshooting.

## Compose prerequisites

The README recommends Docker Desktop for the Compose quickstart. Run the setup commands from the repository root.

## Local environment

Copy .env.example to .env before starting the stack. Keep local credentials out of Git and use placeholders in examples.

## Rules provider

The default TRIAGE_PROVIDER=rules requires no API key or model download. Follow the rules-specific Compose command in the README.

## Ollama provider

For local model inference, select TRIAGE_PROVIDER=ollama and follow the Ollama startup instructions. The initial run downloads the configured model.

## Startup inspection

Use docker compose ps -a to inspect startup. Check service health and the exit codes of the migrate and seed jobs.

## Local addresses

With the documented Compose setup, open http://localhost for the app, http://localhost/docs for API documentation, and http://localhost/ready for readiness.

## Compose logs

Use docker compose logs -f backend to follow backend events. The runbook explains the JSON fields and request identifiers.

## Stopping Compose

The README distinguishes docker compose down, which retains volumes, from docker compose down -v, which deletes them.

## Manual development

The manual setup in the README uses Python 3.12 and Node.js 22, with PostgreSQL and Redis running in containers.

## Backend setup order

Follow the README sequence: create the virtual environment, install development dependencies, apply Alembic migrations, seed data, and start uvicorn.

