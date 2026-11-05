# Disaster Recovery Plan

Phase 0 scope: the API process is stateless; all durable state is one PostgreSQL 16 database
(with `pgvector` and `pg_trgm`). Recovery therefore means restoring the database and redeploying
the process.

## Targets

| Scenario | RTO | RPO | Basis |
|---|---|---|---|
| API process crash / bad deploy | 5 min | 0 | stateless process, rolling restart |
| Database instance loss (single node) | 30 min | ≤ 15 min | restore latest base backup + WAL |
| Corrupted / partially applied migration | 60 min | ≤ 15 min | restore, then re-apply migrations up to the last known-good revision |
| Region loss | out of scope (prototype) | — | single-region deployment by design |

RPO assumes WAL archiving or managed backups with point-in-time recovery at ≤15 min granularity.
Until that exists, the honest RPO is "since the last logical dump" — say so rather than quoting a
number the system cannot meet.

## Backups

| What | How | Frequency | Retention |
|---|---|---|---|
| Database | `pg_dump -Fc` (or managed PITR) | daily full, 15 min WAL | 7 days |
| Migrations | git (`migrations/versions/`) | per commit | permanent |
| Source corpus files | object storage, referenced by content hash | per ingestion | permanent |
| Run artefact / event log | inside the database | with the database | permanent |

Verify restores, do not assume them: `pg_restore` into a scratch database monthly and run
`alembic upgrade head` plus `pytest -m integration` against it.

## Recovery procedure — database

1. Declare the incident and freeze deploys (no migrations during recovery).
2. Provision a PostgreSQL 16 instance; confirm `select extname from pg_extension` includes
   `vector` and `pg_trgm` after restore (recreate them if the dump excluded extensions).
3. Restore the newest base backup, then replay WAL to the target time (just before the incident).
4. Point `DATABASE_URL` at the restored instance.
5. Run `uv run alembic current`; if the dump predates the deployed revision, run
   `uv run alembic upgrade head`.
6. Start one API instance; verify `/readyz`, then `GET /api/v1/...` smoke calls, then scale out.
7. Record the achieved RTO/RPO and the cause in an incident note.

## Recovery procedure — bad migration

1. Stop the API (a schema mismatch produces 5xx and confusing domain errors).
2. If the revision is reversible and no data was written under it: `uv run alembic downgrade -1`.
3. Otherwise restore from backup and re-apply up to the last known-good revision — prefer this over
   hand-editing a live schema.
4. Fix the migration, add a regression test, redeploy.

## Recovery procedure — process / deploy

1. Roll back to the previous image (stateless, no data migration involved).
2. Confirm `/healthz` (immediately) and `/readyz` (after the pool warms).
3. Inspect `service_starting` log lines for `env`, `auth_mode`, `version`.

## Data integrity checks after recovery

- `select count(*) from shared_event_outbox where status = 'pending'` — an unbounded backlog means
  the outbox relay is not dispatching; replay is safe, handlers key on `event_id`.
- `select max(occurred_at) from shared_audit` — the audit trail must advance with traffic; if it
  does not, the writers are not participating in the transaction.
- `select max(sequence) from shared_event_outbox` — gaps are not expected; a gap means a rolled-back
  transaction, which is fine, but a decreasing maximum means a restore went too far back.

Authentication recovery: `docs/dr-plan-identity-access.md` (key-table restore, revocation after
restore, credential compromise). Keys are hashed; plaintext is never backed up.

Stakeholder model recovery: `docs/dr-plan-stakeholder-model.md` (persona cards, allowlist, in-memory limitation).
Claim validation recovery: `docs/dr-plan-claim-validation.md` (migration 0301, claims, reference figures).

Evidence retrieval recovery: `docs/dr-plan-evidence-retrieval.md` (pack table restore, snapshot/
index consistency checks, reweighted pack lineage).

## Communication

Single operator (hackathon prototype): record the incident in the project workpad with timeline,
cause, achieved RTO/RPO and follow-up. Notify the jury-facing owner before a demo if the data
restore lost runs.
