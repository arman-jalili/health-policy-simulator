# Runbook — SimulationOrchestration

Operational procedures for the background simulation worker and progress stream. Canonical
architecture: `.pi/architecture/modules/simulation-orchestration.md`; runtime decision:
`.pi/architecture/decisions/ADR-013-simulation-orchestration-runtime-integration.md`.

## Service shape

| Item | Value |
|---|---|
| Entry path | `shared.app.create_app` → `simulation_orchestration.composition.build_container` → router + lifespan worker |
| Public API | `POST /api/v1/runs/{run_id}:start`, `GET /runs/{run_id}/stream`, `POST /runs/{run_id}:pause`, `POST /runs/{run_id}:resume`, `GET /runs/{run_id}/usage`, `GET /jobs/{job_id}` |
| Persistence | Migrations `0302_simulation_orchestration` + `0303_simulation_lease` + `0304_simulation_pause_reason`: `_job`, `_invocation`, `_progress`, `_prompt` |
| Memory mode | explicit `PERSISTENCE=memory`; test/local only |
| Worker | in-process task `simulation-worker`; supervised, per-job failure isolation, 60 s job lease |
| Readiness | `/readyz` reports `simulation_orchestration`, `simulation_orchestration_persistence`, `simulation_model` |
| Metrics | `simulation_jobs_started_total`, `_completed_total`, `_invocations_total`, `_tokens_total`, `_cost_total`, `_progress_events_total`, `_budget_exhausted_total`, `simulation_job_failures_total`, `simulation_worker_restarts_total` |
| Logs | structlog JSON; boot event `simulation_orchestration_wired`; worker request logs carry trace ids |

## Startup sequence

1. `alembic upgrade head` — must reach `0304_simulation_pause_reason`.
2. Set `DATABASE_URL`, `PERSISTENCE=postgres`, and a supported `SIMULATION_MODEL_ID`
   (currently `scripted-local`); an unknown model aborts boot with `UNKNOWN_MODEL`.
3. Start `hps-api`.
4. `GET /healthz` → 200.
5. `GET /readyz` → 200 with `checks.simulation_orchestration == "ok"` and the configured
   persistence/model.
6. `POST /api/v1/runs/{run_id}:start` → 202. The worker must move the job to `completed` and
   `GET /runs/{run_id}/stream` must show `run.started` → `run.completed` without a manual step.
7. `GET /runs/{run_id}/usage` reports the bootstrap turns' metered envelopes; `GET /jobs/{id}`
   `budget_used` matches the usage report. A budget of 1 pauses after the first invocation with
   `run.budget_exhausted`.

## Graceful shutdown

The lifespan sets the worker stop event and waits up to 2 seconds. In-flight PostgreSQL writes are
committed by the service/repository transaction. If the process is killed, a `running` job remains
resumable; on the next boot the worker re-queues RUNNING jobs, logs
`simulation_worker_recovered`, and continues from the last checkpoint. A live worker renews its lease
on every claim (60 s default); an expired lease makes the job claimable again.

## Common failure modes

| Symptom | Cause | Recovery |
|---|---|---|
| Boot fails `UNKNOWN_MODEL` | Unsupported `SIMULATION_MODEL_ID` | Use a configured model; never meter zero |
| Job stuck `queued` | Worker task not started / crashed | Check `/readyz` `simulation_worker`; inspect `simulation-worker` logs; restart process |
| Job `dead_letter` | Retry limit reached (default 3) | Read `error` via `GET /jobs/{id}`; fix the cause, then re-queue manually only after review |
| Job `running` with no progress | Worker died; lease not yet expired | Wait for the 60 s lease or restart; boot recovery re-queues RUNNING jobs |
| `/readyz` `simulation_worker: dead` | Worker task finished unexpectedly | Supervisor restarts it and increments `simulation_worker_restarts_total`; check logs if it stays dead |
| `/readyz` red | Database unreachable | Restore DB; process stays live but not ready |
| SSE reconnect repeats events | Client reused an old `Last-Event-ID` | Use the last received `id:`; server replays strictly after it |
| Duplicate progress sequence | A non-application writer bypassed the store allocator | Use `append` with sequence 0; the store serialises allocation under a per-run advisory lock |
| Invocation duplicate | Provider retried an existing id | Append-once is intentional; inspect the existing envelope |
| Budget exhaustion | `max_cost`/`max_tokens`/`max_invocations` breached before a turn | Inspect `error` and `budget_used`; resume with a raised `budget` body; no rejected invocation is executed |
| `INVALID_JOB_TRANSITION` | Pause/resume from a terminal state | Read `GET /jobs/{id}`; only queued/running pause and paused resume are legal |
| Resume returns `queued`, not `running` | Resume re-queues the job for the worker | Wait for the worker to claim it; inspect `attempts` and progress sequence |

## Incident response and escalation

1. Capture `run_id`, `job_id`, status, checkpoint, last progress sequence and trace id.
2. Stop accepting new starts for the affected run; do not delete progress or invocation rows.
3. Inspect `simulation_orchestration_job`, `_progress`, `_invocation` and the worker logs.
4. Resume from the checkpoint if the job is paused; resume re-queues and the worker continues at the
   next node. Never hand-edit a checkpoint in SQL.
5. Add a regression test before closing the incident.
6. Escalate to the single prototype owner.

## Rollback

| Layer | Action |
|---|---|
| Process | Redeploy previous image; worker stops with the process |
| Schema | `alembic downgrade 0302_simulation_orchestration` (drops the lease column first), then `0301_claim_validation` if the tables must go |
| Data | Restore the pre-change dump before downgrading if jobs/invocations must be retained |
| Code | Revert the MR |
