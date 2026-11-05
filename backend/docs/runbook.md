# Runbook

Operational procedures for the health-policy-simulator API. Phase 0 scope: one process
(`shared.app:create_app`) and one PostgreSQL 16 database with `pgvector` and `pg_trgm`.

## Service shape

| Item | Value |
|---|---|
| Entrypoint | `hps-api` (equivalently `uvicorn shared.app:create_app --factory`) |
| Liveness | `GET /healthz` — process only, never touches the database |
| Readiness | `GET /readyz` — `SELECT 1`; `503 NOT_READY` when the database is unreachable |
| Logs | JSON on stdout; every line of a request carries `trace_id` |
| Trace id | caller `X-Request-ID` (8–64 chars of `[A-Za-z0-9._:-]`) or generated; echoed in responses |
| Config | environment only (`DATABASE_URL` required); validated at boot |

## Boot failure: `ConfigError: Invalid configuration`

1. Read the message — it names the offending variable (`DATABASE_URL: ...`).
2. Confirm `.env` exists and matches `.env.example`, or that the orchestrator injected
   `DATABASE_URL`.
3. Do not start the process with a guessed URL: a wrong DSN surfaces later as opaque 503s.

## Alert: `readyz` returns 503 (`code: NOT_READY`)

1. Grab `trace_id` from the response body; find the matching `readiness_check_failed` log line.
2. Check database reachability from the pod/host:
   `psql "$DATABASE_URL" -c "select 1"` (strip the `+asyncpg` suffix for `psql`).
3. Check `pg_stat_activity` for exhausted connections. Tune `DB_POOL_SIZE` /
   `DB_MAX_OVERFLOW` per replica; total across replicas must stay below `max_connections`.
4. If the database is healthy but readiness still fails, check DNS and the `DB_CONNECT_TIMEOUT_S`
   budget against pgbouncer/network policy.
5. `/healthz` staying 200 while `/readyz` fails is intentional: do not restart-loop the process to
   "fix" a dependency outage.

## Alert: `AUTH_MODE=demo` in a non-local environment

The process logs `demo_auth_mode_enabled` at startup and refuses to boot when
`ENV=production`. Remediation: set `AUTH_MODE=strict` and restart. Demo mode must never be the
reason anonymous writes are accepted.

## Migration procedure

```bash
uv run alembic current         # verify the revision
uv run alembic upgrade head    # apply
uv run alembic downgrade -1    # revert the last revision (only when the previous revision is safe)
```

Rules:

- Migrations and the application deploy together; never run the new app code against an old schema.
- `0000_bootstrap` enables `vector` and `pg_trgm`; a downgrade keeps the extensions on purpose.
- A failing migration leaves the revision chain untouched (single transaction per revision).
- Before any destructive migration, take a snapshot (see `dr-plan.md`).

## Restart / drain

1. Stop accepting traffic (remove from the load balancer) and wait for in-flight requests; the API
   is stateless, so a hard restart loses no domain state.
2. Terminate; the process disposes the database pool on shutdown (`service_stopped` log line).
3. Start the new process; confirm `/healthz` then `/readyz`.

## Request-level failure triage

- `code` is stable: `VALIDATION_FAILED`, `NOT_FOUND`, `NOT_READY`, `UNAUTHORIZED`, `FORBIDDEN`,
  `INTERNAL_ERROR`. Branch on `code`, never on `message`.
- `INTERNAL_ERROR` responses are generic by design; the trace id links to the full traceback in the
  logs (`request_failed` with `error_type` and `exc_info`).
- 5xx increase after a deploy usually means a schema/exception-handling mismatch — check
  `alembic current` against the running image.

## Incident response

Severity is about the demo, not about aesthetic correctness:

| Severity | Definition | Response |
|---|---|---|
| SEV-1 | `/readyz` failing, data loss, or wrong published output | stop deploys, restore service, notify the demo owner |
| SEV-2 | degraded latency, failing ingestion, guard false negatives | fix within the working session, record the workaround |
| SEV-3 | cosmetic/UX, missing non-critical metric | queue as an issue |

Procedure:

1. Open an incident note with start time, symptom, `trace_id` sample.
2. Stabilise before diagnosing: roll back or restore (see below), then investigate.
3. Record achieved RTO/RPO and the root cause in the workpad.
4. Add the regression test that would have caught it — the incident is not closed until it exists.

Escalation: single operator for the prototype. If the demo owner cannot be reached and the
database is unrecoverable, fall back to the documented demo dataset (see `dr-plan.md`) rather than
presenting numbers that cannot be traced to a page.

## Rollback

| Layer | Command | Notes |
|---|---|---|
| Process image | redeploy previous version | stateless; no data migration involved |
| Schema | `uv run alembic downgrade -1` | only when the revision is reversible and unused; otherwise restore from backup |
| Configuration | revert the env change and restart | `AUTH_MODE`, `DATABASE_URL` and pool sizes take effect at boot |

Never roll back a published brief: briefs are attributed artefacts. Withdraw with a new version.

## Secret handling

- API keys, `DATABASE_URL` and any `password`/`token`/`authorization` field are redacted by the
  logging processor (`***`). A leaked credential in logs is a bug — open an issue with the trace id.
- Never log request bodies at INFO; they contain corpus text and query parameters.
