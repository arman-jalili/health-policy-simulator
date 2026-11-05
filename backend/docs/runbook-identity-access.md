# IdentityAccess Runbook

Operational procedures for API-key authentication, scopes and actor attribution
(ADR-005). General service operations live in `docs/runbook.md`; this file covers the
authentication-specific failure modes and the key lifecycle.

## Service shape

| Item | Value |
|---|---|
| Context | `src/identity_access/` (adapter depth, ADR-008) |
| Entry point | `shared.app.create_app` → `build_identity_access_container` → `app.state.identity_access` |
| Guard | `require_declared_scope` on every `/api/v1` route; health routes are auth-free |
| Key table | `identity_access_api_key` (migration `0104_identity_access`) |
| Hashing | salted SHA-256; only `key_hash` + `salt` are stored |
| Admin routes | `POST/GET /api/v1/admin/keys`, `DELETE /api/v1/admin/keys/{key_id}` |
| Readiness | `GET /readyz` reports `checks.database` and `checks.llm` (no auth) |

## Startup sequence and dependencies

1. `DATABASE_URL` must be set; a missing/malformed DSN aborts boot.
2. Apply migrations: `uv run alembic upgrade head` must reach `0104_identity_access`.
3. `PERSISTENCE=postgres` (default) uses the hashed key store; `memory` is local-only.
4. `AUTH_MODE=strict` requires `X-API-Key` on every `/api/v1` route. `demo` is loopback-only and
   refused when `ENV=production` (boot fails with `AUTH_MODE=demo is refused...`).
5. Bootstrap the first admin key once (the store has no key yet):

   ```bash
   # Inside a trusted shell with the app's database settings:
   # POST /api/v1/admin/keys requires an admin key; bootstrap via the container instead:
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
       print(issued.key)  # printed exactly once; store it in the secret manager
       await app.state.db.dispose()

   asyncio.run(main())
   PY
   ```

   The plaintext is not recoverable later; if it is lost, issue a new admin key from an existing
   admin key or re-run the bootstrap procedure against a database with no admin key.

6. Confirm `GET /healthz`, then `GET /readyz` (`checks.database == "ok"`).

## Configuration reference

| Variable | Default | Notes |
|---|---|---|
| `DATABASE_URL` | required | asyncpg DSN; the key table lives here |
| `PERSISTENCE` | `postgres` | `memory` is refused outside `ENV=local` |
| `AUTH_MODE` | `demo` | `strict` in every shared environment; `demo` + `production` refuses boot |
| `ENV` | `local` | drives the demo/production guard |
| `LLM_HEALTH_URL` | unset | optional; `/readyz` reports `not_configured` when unset |
| `DB_CONNECT_TIMEOUT_S` | `5.0` | DB and LLM readiness probe budget |

## Key lifecycle

- **Create:** admin key → `POST /api/v1/admin/keys` with `{label, role}` → `201` contains `key`
  exactly once. Store it immediately; never log it.
- **List:** `GET /api/v1/admin/keys` returns metadata only (no hash, no plaintext).
- **Revoke:** `DELETE /api/v1/admin/keys/{key_id}` → `204`; the next request with that key is `401`.
- **Scope refusal:** a valid key without the required scope is `403 SCOPE_REQUIRED` with the missing
  scope in `details[].code`.
- **Roles:** analyst = runs/briefs read+write; operator = analyst + corpus read/write + briefs
  publish; admin = wildcard.

## Common failure modes

| Symptom | Meaning | Action |
|---|---|---|
| `401 UNAUTHENTICATED` on every route | strict mode, missing/unknown/revoked key, or no key store bound | send `X-API-Key`; verify the key id in the DB; check `KEY_STORE_UNAVAILABLE` logs |
| `403 SCOPE_REQUIRED` | valid key, insufficient scope | inspect `details[].code`; issue a key with the right role |
| `503 KEY_STORE_UNAVAILABLE` | composition root did not bind `api_key_admin` | verify `app.state.identity_access` is present and the boot log has no config error |
| Boot refuses `AUTH_MODE=demo` | `ENV=production` + `AUTH_MODE=demo` | set `AUTH_MODE=strict`; restart |
| Every key suddenly 401 | revoked, restored from an older backup, or wrong database | list keys; re-issue; check `DATABASE_URL` points at the intended DB |
| `X-API-Key` appears in logs | redaction regression | open a bug; logs must show `***` for credentials |
| `/readyz` 503 with `checks.llm` failing | configured LLM health URL unreachable | fix the URL/service; `not_configured` is not a failure |

## Observability

- Structured logs: `service_starting` (env, auth_mode, version), `demo_auth_mode_enabled`,
  `request_rejected` (error code/status, trace id), `http_request` (method, path, status, duration).
- Trace id: caller `X-Request-ID` or generated; echoed as `X-Request-ID`/`X-Trace-Id`.
- Metrics: `/metrics` exposes HTTP and domain-event counters.
- Health: `/healthz` liveness; `/readyz` DB + optional LLM.
- Audit/attribution: outbox rows carry `actor` from `Principal.actor_id()`; empty actors are
  rejected at write time.

## Graceful shutdown

The process is stateless. Remove it from the load balancer, wait for in-flight requests, then
terminate; the lifespan disposes the database pool and logs `service_stopped`. There is no key
state to flush — revocations and issues are committed transactions.

## Incident response and rollback

1. Freeze deploys; capture a trace id and the `request_rejected`/`http_request` lines.
2. If keys are compromised: revoke the affected key ids immediately (`DELETE /api/v1/admin/keys/...`),
   issue replacements, and rotate any key pasted into a ticket/chat.
3. If a deploy regressed auth: roll back the image; schema `0104` is additive and can stay.
4. If the key table is lost/corrupted: restore the database (see `dr-plan-identity-access.md`), then
   verify `GET /readyz` and issue fresh keys; plaintext keys cannot be recovered from hashes.
5. Record the incident, achieved RTO/RPO and the regression test that prevents recurrence.

## Contract proofing

```bash
bash .pi/scripts/ci/check_identity-access_contracts.sh   # 81 checks
bash .pi/scripts/ci/stage_identity-access_proofing.sh    # checker + 80% coverage gate
```
