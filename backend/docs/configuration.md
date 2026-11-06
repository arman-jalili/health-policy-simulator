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

## LLM provider

| Variable | Default | Effect |
|---|---|---|
| `LLM_PROVIDER` | `scripted` | `scripted` is local/test only; `openai-compatible` and `azure_ai_foundry` select `HttpLlmClient` |
| `LLM_BASE_URL` | — | Provider base URL, e.g. `https://api.openai.com/v1` |
| `LLM_API_KEY` | — | Secret-shaped; required for every non-scripted provider |
| `LLM_MODEL` | `gpt-4o-mini` | Model id sent to the provider and used by the price table |
| `LLM_TIMEOUT_S` | `30` | Per-request timeout |
| `LLM_MAX_RETRIES` | `2` | Retries on timeout, 429 and 5xx; exhausted retries fail the run |
| `LLM_TEMPERATURE` | `0.2` | Sampling temperature |
| `LLM_MAX_OUTPUT_TOKENS` | `1024` | Completion cap |

A real provider without `LLM_BASE_URL` or `LLM_API_KEY` aborts boot with a named reason. `scripted`
outside `ENV=local` is refused; `/readyz` reports which provider is bound.

## Test database isolation

Integration tests derive `TEST_DATABASE_URL` as `<DATABASE_URL database>_test` when it is not set
explicitly. Destructive migration fixtures refuse a database whose name does not end in `_test`
unless `ALLOW_DESTRUCTIVE_TESTS=1` is set. The demo database and the test database are therefore
separate; `make demo-reset` re-seeds the demo if it was modified by hand.

## Simulation metering

| Variable | Default | Effect |
|---|---|---|
| `SIMULATION_MODEL_ID` | `scripted-local` | Model id when `LLM_PROVIDER=scripted`; an unknown id aborts boot |
| `SIMULATION_INPUT_PRICE_PER_1K` | `0.0` | EUR per 1k input tokens, applied when an invocation envelope is recorded |
| `SIMULATION_OUTPUT_PRICE_PER_1K` | `0.0` | EUR per 1k output tokens |
| `SIMULATION_ALLOW_ZERO_PRICE` | `true` | When `false`, boot refuses a model priced at zero |
| `SIMULATION_STREAM_IDLE_S` | `3600` | Max seconds an SSE stream may be idle before `run.stream_closed` (`max_idle`) |
| `SIMULATION_STREAM_HEARTBEAT_S` | `15` | Seconds between `: ping` heartbeat comments while idle |

Zero prices are permissive by default so a local demo runs without a price list, and
`/readyz` reports `simulation_pricing: configured|zero` so the posture is visible rather than implicit.
Set `SIMULATION_ALLOW_ZERO_PRICE=false` in staging and production: a deployment that forgot to price the
model should fail at boot, not meter every run at `0.0`.
