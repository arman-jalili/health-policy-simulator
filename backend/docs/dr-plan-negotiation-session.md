# DR plan: NegotiationSession

Canonical: `docs/runbook-negotiation-session.md`

## Targets

| Scenario | RTO | RPO |
|---|---:|---:|
| API instance loss | 0 (re-open the run) | run state (memory) lost |
| Process restart | 0 | run state (memory) lost |
| PostgreSQL primary loss | 15 min | last outbox/event row once migrations `0401`/`0402` land |
| Guard unbound | 0 | none: writes fail closed |

## Backup and restore

1. Today the negotiation aggregate and run log live in the process (memory adapters). There is no
   durable copy, so a restart is a new corpus of runs. Communicate this before any restart.
2. When the SQLAlchemy family lands, the only state to back up is the run aggregate tables plus the
   append-only run log (`0401`, `0402`). Back them up with the normal PostgreSQL schedule.
3. Restore order: database → `alembic upgrade head` → application. `/events` must replay every
   event and the fold must equal the live projection (proof: `test_replay_behaviour.py`).
4. Never rebuild run state from the outbox alone; the run log is the replay source.

## Failover

- The service is stateless between requests except for the in-memory store; a replacement replica
  cannot serve runs opened on the lost replica. With the SQLAlchemy family, all replicas share the
  run log and failover is transparent because `save` writes the aggregate and log in one
  transaction.
- SSE reconnects must send `Last-Event-ID`; replay is contiguous by per-run ordinal, so a client
  that reconnects after failover receives every frame it missed (in-process today).

## Integrity checks

- `GET /runs/{id}/events` sequences are gap-free and start at 1.
- Folding the log to round N equals `GET /runs/{id}` state for that run (replay equivalence).
- Every `ArgumentSubmitted` carries `invocation_id`; every `PositionRevised` carries cited ids.
- A closed run rejects every command with `CLOSED_RUN_IMMUTABLE` while `/events` still replays.
- `/metrics` shows no rising 5xx rate on `/api/v1/runs*`; guard rejections are 4xx by code.

## Gap tracking

The durable-store gap is owned by the module roadmap and remains visible in the runbook until
migrations `0401`/`0402` and their SQLAlchemy adapters are merged. Do not claim restart durability
before that.
