# Configuration and the readiness env rule

Canonical: `src/shared/config.py`, `.env.example`, `.pi/scripts/ci/check_env_placeholders.sh`.

## Local setup

```bash
cp .env.example .env
alembic upgrade head
hps-api
```

`.env.example` documents the local defaults. Copying it verbatim is the supported setup; the
documented PostgreSQL URL is **not** a secret and is expected to stay identical.

## What the readiness gate checks

`validate-architecture-readiness.sh` runs the architecture conformance check, which calls
`check_env_placeholders.sh` when both `.env` and `.env.example` exist.

| Rule | Meaning |
|---|---|
| Non-secret variables may equal `.env.example` | `DATABASE_URL`, ports, log levels and feature flags are defaults, not credentials |
| Secret-shaped variables must differ from `.env.example` | names matching `SECRET`, `TOKEN`, `PASSWORD`, `PASSWD`, `PRIVATE_KEY`, `API_KEY`, `ACCESS_KEY`, `SECRET_KEY`, `CREDENTIAL`, `DSN` |
| Secret-shaped placeholders always fail | `change-me`, `changeme`, `example`, `example-*`, `replace-me`, `your-*`, `secret`, `test`, `xxx`, `todo`, `placeholder` |
| Failures name the variable | e.g. `API_KEY: secret-shaped value is still a placeholder` |

`DATABASE_URL` is explicitly exempt because the documented local DSN contains fixed development
credentials and must remain copy-pasteable. A production DSN injected by the orchestrator is never
compared with the example.

## Examples

Pass — the documented local setup:

```dotenv
DATABASE_URL=postgresql+asyncpg://hps:hps@localhost:5433/health_policy
```

Fail — placeholder secret:

```dotenv
API_KEY=change-me
```

Fail — secret copied unchanged from the example:

```dotenv
APP_SECRET=some-example-value   # same value in .env.example
```
