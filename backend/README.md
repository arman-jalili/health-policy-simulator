# health-policy-simulator

Institutional negotiation simulator for Austrian healthcare policy: nine grounded agents argue a
policy question on citation-grade evidence, and the result is an auditable decision brief.

**Status:** Phase 0 (bootstrap) — shared kernel, configuration, migrations and health probes only.
No bounded context is implemented yet. See
[`.pi/architecture/implementation-roadmap.md`](.pi/architecture/implementation-roadmap.md).

## Stack

| Concern | Choice |
|---|---|
| Runtime | Python 3.12, FastAPI, uvicorn |
| Persistence | PostgreSQL 16 + SQLAlchemy 2.x async (asyncpg), Alembic |
| Extensions | `pgvector` (embeddings) and `pg_trgm` (lexical search) enabled at bootstrap |
| Config | pydantic-settings, fail-fast, `.env` for local |
| Logging | structlog JSON with trace-id context and credential redaction |
| Architecture | DDD bounded contexts, modular monolith ([ADR-001](.pi/architecture/decisions/ADR-001-architecture-pattern.md)) |

## Quickstart

```bash
# 1. Toolchain
uv sync                       # creates .venv from pyproject.toml (dev extras by default)

# 2. Configuration
cp .env.example .env

# 3. Database
docker compose up -d db
uv run alembic upgrade head

# 4. Run
uv run hps-api                # or: uv run uvicorn shared.app:create_app --factory --reload

# 5. Verify
curl -s localhost:8000/healthz
curl -s -i localhost:8000/readyz   # 200 when the database answers, 503 NOT_READY otherwise
```

OpenAPI is served at `/docs` and `/openapi.json`.

## Commands

| Command | Purpose |
|---|---|
| `uv run ruff check .` | Lint |
| `uv run ruff format --check .` | Format check (`ruff format .` to apply) |
| `uv run mypy` | Type check (strict; `src` + `tests`) |
| `uv run pytest` | Unit tests |
| `uv run pytest -m "not integration"` | Unit tests without a database |
| `uv run pytest -m integration` | Migration and outbox round-trip against `DATABASE_URL` |
| `uv run alembic upgrade head` | Apply migrations |
| `uv run alembic downgrade base` | Revert to an empty schema |
| `bash .pi/scripts/validate-architecture.sh` | Architecture validators |
| `python3 .pi/scripts/ci/check_modeling_depth.py` | ADR-008 modeling-depth check |
| `bash .pi/scripts/ci/run_preflight.sh` | Guardian preflight suite |

## Layout

```
src/
  shared/                 # shared kernel — no domain vocabulary
    app.py                # composition root (create_app, console entrypoint)
    config.py             # pydantic-settings, fail-fast, demo/production guard
    errors.py             # AppError hierarchy + error envelope
    enums.py              # technical enums only
    ids.py                # prefixed ULIDs
    clock.py              # injectable UTC clock
    db.py                 # engine, session factory, declarative Base
    outbox.py             # transactional outbox writer + row
    audit.py              # append-only audit trail writer
    log_setup.py          # structlog JSON + redaction
    http/                 # middleware, error handlers, health probes, dependencies
migrations/
  versions/0000_bootstrap.py
tests/
  unit/                   # fast, no I/O
  integration/            # requires PostgreSQL (marker: integration)
```

Bounded contexts are added in Phase 1 as `src/<context>/{domain,application,infrastructure,interfaces}/`.
`shared/` is the only exempt directory; every other top-level package must be a context.

## Configuration

Required: `DATABASE_URL`. Everything else has a safe default; see `.env.example`.

`PERSISTENCE` selects the adapter family: `postgres` (default) or `memory`. Memory is explicit, is
intended for tests and a database-less local demo, and is refused outside `ENV=local`.

Three boot-time guards are deliberate:

- a missing or malformed `DATABASE_URL` aborts startup instead of serving half a system;
- `AUTH_MODE=demo` with `ENV=production` is refused (ADR-005);
- `PERSISTENCE=memory` outside `ENV=local` is refused: restart would silently destroy the corpus.

## Authentication

`AUTH_MODE=strict` requires `X-API-Key` on every `/api/v1` route; `/healthz` and `/readyz` stay
auth-free. Roles map to scopes: analyst (runs/briefs read+write), operator (+ corpus read/write and
briefs publish), admin (wildcard). Demo mode is loopback-only and refused when `ENV=production`.

Bootstrap the first admin key once against the configured database (plaintext is printed once):

```bash
uv run python - <<'PY'
import asyncio
from identity_access.interfaces.dto import CreateApiKeyCommand
from identity_access.interfaces.types import Role
from shared.app import create_app
from shared.config import get_settings

async def main() -> None:
    app = create_app(get_settings())
    issued = await app.state.identity_access.api_key_admin.create_key(
        CreateApiKeyCommand(label="bootstrap-admin", role=Role.ADMIN)
    )
    print(issued.key)
    await app.state.db.dispose()

asyncio.run(main())
PY
```

Then use that key against `POST/GET /api/v1/admin/keys` and `DELETE /api/v1/admin/keys/{key_id}`.
Keys are stored as salted SHA-256 hashes; revocation takes effect on the next request. Operations:
`docs/runbook-identity-access.md`; recovery: `docs/dr-plan-identity-access.md`. Contract proofing:
`bash .pi/scripts/ci/check_identity-access_contracts.sh`.

## Migration policy

- One revision chain, table names prefixed with the owning context (`shared_event_outbox`,
  `evidence_corpus_document`, …, per ADR-002) so ownership is visible at a glance.
- `0000_bootstrap` enables `pgvector` + `pg_trgm` and creates the shared outbox and audit tables.
- `0101` owns document/publication/article/passage, `0102` the search index, `0103` snapshots and
  ingestion runs. Revision identifiers keep their roadmap names; the chain order is authoritative.
- The downgrade drops tables but keeps the extensions: later revisions depend on them and dropping
  `vector` requires superuser rights on managed databases.

## Notes for operators

- `/healthz` is liveness only and stays 200 while the database is down; use `/readyz` for ingress
  and deployment gating.
- Every request gets a trace id (caller-supplied `X-Request-ID` or generated), echoed in the
  response headers and in `trace_id` of every error envelope.
