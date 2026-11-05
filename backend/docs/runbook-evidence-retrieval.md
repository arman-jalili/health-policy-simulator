# Runbook — EvidenceRetrieval

Operational procedures for the evidence-retrieval context. Canonical architecture:
`.pi/architecture/modules/evidence-retrieval.md`; runtime decision:
`.pi/architecture/decisions/ADR-010-evidence-retrieval-runtime-integration.md`.

## Service shape

| Item | Value |
|---|---|
| Entry path | `shared.app.create_app` → `evidence_retrieval.composition.build_container` → router |
| Public API | `/api/v1/evidence/candidates`, `/api/v1/evidence/packs`, pack read/score/reweight |
| Scopes | `runs:read` for search/read, `runs:write` for assemble/reweight |
| Persistence | `PERSISTENCE=memory` (explicit local/tests) or PostgreSQL pack table |
| Migration | `0201_evidence_retrieval` |
| Readiness | `GET /readyz` includes `evidence_retrieval`, `evidence_retrieval_mode` and capability detail |
| Logs | JSON with `trace_id`; every request has one access line |
| Metrics | `evidence_retrieval_searches_total`, `_candidates_total`, `_packs_total`, `_reweights_total` |

## Startup sequence

1. Apply migrations: `uv run alembic upgrade head` (must reach `0201_evidence_retrieval`).
2. Start `hps-api` (or `uvicorn shared.app:create_app --factory`).
3. Confirm `GET /healthz` returns `200`.
4. Confirm `GET /readyz` returns `200` and `checks.evidence_retrieval == "ok"`.
5. Smoke: `POST /api/v1/evidence/candidates` with a known claim and snapshot.

The corpus container is built before retrieval; retrieval consumes only corpus published ports.

## Graceful shutdown

1. Remove the process from the load balancer and wait for in-flight requests.
2. Send SIGTERM; the shell cancels the outbox relay and disposes the database pool.
3. The process is stateless apart from frozen packs; a hard restart loses no committed pack.

## Common failure modes

| Symptom | Likely cause | Recovery |
|---|---|---|
| `/readyz` 503 with `field=evidence_retrieval` | A configured dense/reranker dependency became unreachable | Restore provider connectivity; do not silently serve lexical-only results as hybrid. Check `readiness_check_failed` logs by `trace_id`. |
| `POST /evidence/packs` 503 | Corpus snapshot/index unavailable | Verify corpus `/readyz`, snapshot exists, index manifest is current; re-pin if needed. |
| `POST /evidence/packs` 409 `PACK_FROZEN` / 422 `CANDIDATE_WITHOUT_PROVENANCE` | Client tried to mutate a frozen pack or evidence lacked provenance | Create a new pack; investigate corpus provenance. |
| `GET /packs/{id}` 404 `EVIDENCE_PACK_NOT_FOUND` | Wrong id or pack not persisted | Check `PERSISTENCE` and the `evidence_retrieval_pack` table. |
| Empty candidates for a German compound | Index not populated or rewrite not applied | Verify the corpus index has the passage and the expanded query path; check `evidence_retrieval_searches_total`. |
| Migration mismatch | App started before `0201` | Run `alembic upgrade head`, restart. |

## Configuration reference

| Variable | Effect |
|---|---|
| `PERSISTENCE` | `postgres` (default) uses the SQLAlchemy pack repository; `memory` is local/tests only |
| `DATABASE_URL` | Required for PostgreSQL mode; pack and corpus share the database |
| `AUTH_MODE` | `strict` requires `X-API-Key`; `demo` is loopback-only |
| `LLM_HEALTH_URL` | Optional readiness probe; unset is `not_configured`, not a failure |

The prototype binds local `hashing-char3gram-v1` and `overlap-reranker-v1` adapters, so
`/readyz` reports `lexical+dense` without an external provider. Replacing them with a vendor
encoder keeps the same ports; update the readiness detail and index manifest model id together.

## Incident response and escalation

1. Open an incident note with start time, symptom and a sample `trace_id`.
2. Stabilise: roll back the image or restore the pack table (see DR plan) before diagnosing.
3. Record achieved RTO/RPO and root cause.
4. Add a regression test; the incident is not closed until it exists.
5. Escalate to the single prototype owner; if unavailable and the database is unrecoverable, use
   the documented demo dataset rather than presenting untraceable evidence.

## Rollback

| Layer | Action |
|---|---|
| Process | Redeploy the previous image; packs are immutable and safe to keep |
| Schema | `uv run alembic downgrade -1` only when the revision is unused; otherwise restore |
| Configuration | Revert env and restart |
| Bad pack | Freeze a new version; never edit a frozen pack |
