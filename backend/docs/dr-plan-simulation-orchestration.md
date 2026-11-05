# Disaster Recovery Plan — SimulationOrchestration

Canonical architecture: `.pi/architecture/modules/simulation-orchestration.md`.
Runtime decision: `.pi/architecture/decisions/ADR-013-simulation-orchestration-runtime-integration.md`.

## Scope and targets

SimulationOrchestration owns jobs, metered invocation envelopes, ordered progress events and prompt
versions. It is durable in PostgreSQL mode via migration `0302_simulation_orchestration`; memory
mode is non-durable and local/test only.

| Scenario | RTO | RPO | Basis |
|---|---|---|---|
| API/worker process crash | 5 min | 0 | PostgreSQL commits; job checkpoint is resumable |
| Bad deploy | 5 min | 0 | previous image + same schema |
| Corrupt/missing orchestration tables | 30 min | ≤ 24 h | database backup/PITR |
| Lost progress stream | 10 min | 0 | replay from `Last-Event-ID` / `_progress` |
| Cost-metering loss | 30 min | ≤ 24 h | restore `_invocation`; provider invoices remain authoritative |
| Region loss | out of scope | — | single-region prototype |

## Backup strategy

| What | How | Frequency | Retention |
|---|---|---|---|
| `simulation_orchestration_job` | `pg_dump` / PITR | daily full + WAL | 30 days |
| `simulation_orchestration_invocation` | `pg_dump` / PITR | daily full + WAL | 30 days |
| `simulation_orchestration_progress` | `pg_dump` / PITR | daily full + WAL | 30 days |
| `simulation_orchestration_prompt` | `pg_dump` / PITR | daily full + WAL | 30 days |
| Code + migrations | git | per commit | permanent |
| Proofing output | CI artifact | per PR | 30 days |

## Restore procedure

1. Restore the repository at the last known-good commit and deploy the previous image if needed.
2. Restore the database from the latest dump/PITR target.
3. `alembic upgrade head`; confirm `alembic current` reports `0302_simulation_orchestration`.
4. Start one API instance; the lifespan worker starts automatically.
5. `GET /healthz` → 200; `GET /readyz` → `simulation_orchestration=ok`,
   `simulation_orchestration_persistence` matches the configured family.
6. Integrity checks:
   ```sql
   select status, count(*) from simulation_orchestration_job group by status;
   select count(*) from simulation_orchestration_invocation;
   select count(*) from simulation_orchestration_progress;
   select name, max(version) from simulation_orchestration_prompt group by name;
   ```
7. Resume `running`/`paused` jobs from their checkpoint; never invent a checkpoint.
8. Replay progress for one known run with `GET /runs/{id}/stream` and compare sequence continuity.
9. Record achieved RTO/RPO and root cause.

## Failover

Start a replacement API/worker against the same database. Job claims use
`FOR UPDATE SKIP LOCKED`, so two workers cannot process the same queued job. If the database is
unavailable, do **not** switch production to memory persistence: it is refused outside
`ENV=local` and would silently lose jobs, progress and metering.

## Integrity checks after recovery

```bash
curl -s localhost:8000/readyz | jq '.checks.simulation_orchestration, .checks.simulation_orchestration_persistence'
curl -s localhost:8000/api/v1/jobs/$JOB_ID | jq '.status, .checkpoint, .progress_sequence'
curl -s localhost:8000/api/v1/runs/$RUN_ID/stream | head
```

- Every `completed` job must have a `run.completed` event at the final sequence.
- A `(run_id, sequence)` pair must be unique; duplicates indicate a broken restore.
- Invocation ids must be unique; duplicates indicate a broken restore, not normal retry.
- Prompt versions are append-only; an existing `name@version` must never change body.

## Communication

Single prototype operator: record timeline, cause, achieved RTO/RPO and follow-up. Notify the demo
owner if a restore loses jobs, progress or metering. Do not present reconstructed invocation costs as
original provider records.
