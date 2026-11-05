# Runbook — StakeholderModel

Operational procedures for the stakeholder-model context. Canonical architecture:
`.pi/architecture/modules/stakeholder-model.md`; runtime decision:
`.pi/architecture/decisions/ADR-011-stakeholder-model-runtime-integration.md`.

## Service shape

| Item | Value |
|---|---|
| Entry path | `shared.app.create_app` → `stakeholder_model.composition.build_container` → router |
| Public API | `/api/v1/stakeholders`, `/stakeholders/{id}`, `/powers`, `/history`, `/runs/{run}/stakeholders:select`, `:bind` |
| Scopes | `runs:read` for registry/history, `runs:write` for select/bind, `admin` for profile/power writes, `corpus:write` for history writes |
| Persona input | `backend/config/personas/*.yaml` — exactly 9 validated cards |
| Persistence | In-memory registry seeded from the 9 persona cards; durable profile storage is a follow-up |
| Readiness | `GET /readyz` reports `stakeholder_model` and the published institution count |
| Logs | structlog JSON with `trace_id`; boot logs `stakeholder_personas_loaded` |
| Metrics | `stakeholder_registrations_total`, `_selections_total`, `_bindings_total`, `_positions_total`, `_authority_rejections_total`, `_allowlist_publishes_total` |

## Startup sequence

1. Ship `backend/config/personas/` with exactly the 9 cards.
2. Start `hps-api` (or `uvicorn shared.app:create_app --factory`).
3. Boot loads every card through `PersonaFactory` and validates: institutional name only, ≥1
   interest, ≥1 constraint, grounded mandate/budget, declared category/period/proposal class.
4. An invalid card aborts construction before the process serves; fix the card and restart.
5. Confirm `GET /healthz` returns `200`.
6. Confirm `GET /readyz` returns `200` with `checks.stakeholder_model == "ok"` and
   `checks.stakeholder_institutions == "9"`.
7. Smoke: `GET /api/v1/stakeholders` returns 9 institutions.

## Graceful shutdown

1. Remove the process from the load balancer and wait for in-flight requests.
2. Send SIGTERM; the shell cancels the outbox relay and disposes the database pool.
3. Persona state is reloaded at the next boot. Any API-registered profile changes in the current
   in-memory runtime are lost on restart — see the durability limitation below.

## Common failure modes

| Symptom | Likely cause | Recovery |
|---|---|---|
| Boot exits with `persona … has no interests/constraints` | Invalid YAML card | Fix the card; do not bypass validation |
| Boot exits with `PERSON_REPRESENTATION_FORBIDDEN` | Persona identity names a natural person / uses an honorific | Replace with the institution name |
| Boot exits with `unknown institution category` / `unknown proposal class` | Vocabulary drift | Use a declared enum value from `domain/values.py` |
| `GET /stakeholders` returns fewer than 9 | Persona directory incomplete or boot used a wrong directory | Restore `config/personas/`; restart |
| `POST :select` returns no items | Mandate has no overlap with any interest topic | Rewrite the mandate or extend aliases deliberately |
| `POST :bind` returns 422 `INCOMPLETE_PROFILE` | Selected institution lacks an interest/constraint | Fix its persona card; restart |
| `POST :bind` returns 403 `INSTITUTION_NOT_ALLOWED` | Institution not in the published allowlist | Re-publish the allowlist from the registry |
| `POST /powers` returns `accepted: false` | Claim lacks a citable `MandateSource` | Supply a statutory/contractual citation; do not allow-list the caller |
| `/readyz` reports `stakeholder_institutions != 9` | Wrong persona set at boot | Restore the 9 cards and restart |

## Durability limitation

The current runtime seeds the registry from validated persona cards and keeps mutable profile,
history and binding state in process memory. Restart restores the 9 cards but not API-registered
changes. Do not present this as durable profile storage; the PostgreSQL profile/binding adapter and
migration are the next deployment step. Historical positions and bindings are audit-relevant, so
treat a restart during a demo as a reset unless the durable adapter has landed.

## Configuration reference

| Variable | Effect |
|---|---|
| `PERSISTENCE` | Adapter family selected by the shell; stakeholder runtime currently uses the in-memory registry family |
| `DATABASE_URL` | Required for the shared database; not yet used for stakeholder profiles |
| `AUTH_MODE` | `strict` requires `X-API-Key`; `demo` is loopback-only |
| Persona directory | `backend/config/personas/` fixed at boot; invalid card aborts |

## Incident response and escalation

1. Open an incident note with start time, symptom, affected institution code and a sample
   `trace_id`.
2. Stabilise: if boot fails, fix/restore the persona card; if runtime fails, restart the process and
   verify `/readyz`.
3. Record whether mutable profile/history state was lost (in-memory limitation) and re-declare it.
4. Add a regression test for the persona/logic failure; the incident is not closed until it exists.
5. Escalate to the single prototype owner. If unrecoverable, use the documented 9-card dataset
   rather than inventing institutions.

## Rollback

| Layer | Action |
|---|---|
| Process | Redeploy the previous image; persona cards are boot input |
| Persona config | Revert the YAML change and restart; boot fails fast on invalid cards |
| Allowlist | Re-run `PublishInstitutionalAllowlist`; the guard replaces the allowlist atomically |
| Code | Revert the MR; no stakeholder migration exists yet |
