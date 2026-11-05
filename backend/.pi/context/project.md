# Project Context

> Single source of truth for project-specific knowledge. All agents load this ONCE.

## Project Overview

- **Name:** health-policy-simulator
- **Version:** 0.1.0 (Phase 0 — bootstrap)
- **Language:** Python 3.12+ (FastAPI, SQLAlchemy 2.x async, Alembic)
- **Type:** Web App — REST + SSE API, modular monolith (DDD bounded contexts)
- **Repository:** arman-jalili/health-policy-simulator (`backend/`)

## Core Principles

1. **Citation-grade provenance** — every published claim resolves to a page in a source document.
2. **Architecture traceability** — implementation files reference `.pi/architecture/modules/` or ADRs.
3. **Read before edit** — never mutate a file you have not read.
4. **Validate early** — `bash .pi/scripts/ci/run_preflight.sh` before committing (activate `.venv`).
5. **Depth follows subdomain type** — tactical / service / adapter, enforced by ADR-008 check.
6. **Domain owns state, orchestration owns sequencing** — graph state is never the source of truth.
7. **Honest absences** — "searched, found nothing" is a first-class result, never an empty list.

## Architecture

### Structure

```
backend/
├── src/
│   └── shared/       # shared kernel: app factory, config, errors, ids, clock, db, outbox, log, http
├── migrations/       # Alembic revision chain (0000_bootstrap)
├── tests/            # unit/ (no I/O) and integration/ (PostgreSQL)
├── docs/             # runbook.md, dr-plan.md
├── .pi/              # architecture source of truth
├── compose.yaml      # PostgreSQL 16 + pgvector for local development
└── pyproject.toml
```

Bounded contexts arrive per phase as `src/<context>/{domain,application,infrastructure,interfaces}/`.
`shared/` is the only exempt package; every other directory under `src/` must be declared in
`.pi/architecture/modeling-depth.json`.

### Key Patterns

- **Error handling:** `AppError` hierarchy → uniform envelope `{code, message, details, trace_id}`
- **Tracing:** `X-Request-ID` → structlog contextvars → `trace_id` in every log line and error body
- **Cancellation:** `asyncio.timeout` around dependency checks; DB sessions roll back on exception
- **Atomic writes:** transactional outbox (`shared_event_outbox`) written in the same transaction
- **Time:** injected `Clock` port, UTC only, ISO-8601 `Z` on the wire
- **Identifiers:** prefixed ULIDs (`doc_01J...`), sortable by creation time

## Quality Gates

### Before Commit
```bash
source .venv/bin/activate && bash .pi/scripts/ci/run_preflight.sh
```

### Before Push
```bash
uv run pytest && uv run ruff check .
```

### Before Merge
```bash
uv run pytest
uv run ruff check .
uv run ruff format --check .
uv run mypy
python3 .pi/scripts/ci/check_modeling_depth.py
```

## Scope Classification

| Scope | Files | Lines | Required Validators |
|-------|-------|-------|---------------------|
| Simple | 1 | < 50 | ci-mr (automated) |
| Moderate | 2-5 | 50-200 | architecture-validator |
| Complex | 5-15 | 200-500 | architecture + security |
| Critical | 15+ or core | 500+ | All validators + human |

## Key Files

| File | Purpose |
|------|---------|
| `.pi/architecture/implementation-roadmap.md` | Phase plan and acceptance criteria |
| `.pi/architecture/decisions/` | Accepted ADRs (stack, depth, storage, API, auth, compliance) |
| `.pi/architecture/modules/` | Canonical module documents (one per bounded context) |
| `src/shared/app.py` | Composition root — the only place contexts are wired together |
| `src/shared/config.py` | Settings, fail-fast validation, demo/production guard |
| `src/shared/outbox.py` | Transactional outbox writer (the only event publication path) |
| `migrations/versions/0000_bootstrap.py` | Extensions + shared tables |
| `docs/runbook.md` | Operations, incident response, rollback |

## Commands

| Command | Purpose |
|---------|---------|
| `uv sync` | Install dependencies |
| `uv run hps-api` | Run the API locally |
| `uv run pytest -m "not integration"` | Unit tests |
| `uv run pytest -m integration` | Migration/outbox tests (needs `DATABASE_URL`) |
| `uv run ruff check .` / `uv run mypy` | Lint / type check |
| `uv run alembic upgrade head` | Apply migrations |
| `docker compose up -d db` | Local PostgreSQL 16 + pgvector |
| `bash .pi/scripts/ci/run_preflight.sh` | Local preflight suite |
