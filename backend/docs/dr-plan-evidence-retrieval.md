# Disaster Recovery Plan — EvidenceRetrieval

Canonical architecture: `.pi/architecture/modules/evidence-retrieval.md`.
Runtime decision: `.pi/architecture/decisions/ADR-010-evidence-retrieval-runtime-integration.md`.

## Scope and targets

EvidenceRetrieval stores frozen `EvidencePack` payloads in `evidence_retrieval_pack` (JSONB). The
corpus source passages and index live in the EvidenceCorpus tables. Recovery therefore restores the
shared PostgreSQL database and redeploys the stateless API.

| Scenario | RTO | RPO | Basis |
|---|---|---|---|
| API process crash / bad deploy | 5 min | 0 | stateless process; packs committed |
| Pack table corruption / accidental delete | 30 min | ≤ 15 min | restore + PITR |
| Database instance loss | 30 min | ≤ 15 min | base backup + WAL |
| Corpus index loss | 60 min | since re-ingest | re-index from source files |
| Region loss | out of scope | — | single-region prototype |

## Backup strategy

| What | How | Frequency | Retention |
|---|---|---|---|
| `evidence_retrieval_pack` | `pg_dump -Fc` / managed PITR | daily full, 15 min WAL | 7 days |
| Corpus source files | object storage by content hash | per ingestion | permanent |
| Migrations | git (`migrations/versions/`) | per commit | permanent |
| Evaluation reports | CI artifact | per evaluation run | 30 days |

Frozen packs are immutable, so a restored pack is safe to reuse as-is. Recomputing a pack requires
the same snapshot, index manifest and embedding/reranker model ids named in its trace. The current
dense adapter is deterministic (`hashing-char3gram-v1`); a vendor encoder must be re-indexed or
restored with the same model.

## Restore procedure

1. Declare the incident and freeze deploys/migrations.
2. Provision PostgreSQL 16 with `vector` and `pg_trgm`; restore the newest base backup.
3. Replay WAL to just before the incident.
4. Point `DATABASE_URL` at the restored instance.
5. `uv run alembic current`; if behind, `uv run alembic upgrade head` (must reach `0201`).
6. Start one API instance; verify `/healthz`, `/readyz` with `evidence_retrieval == ok`.
7. Smoke: read a known pack by id; search a known claim; verify candidate ids match the trace.
8. Record achieved RTO/RPO and root cause.

## Failover

The prototype runs one API process and one database. Failover means:

1. Promote/replace the database instance.
2. Start a new API process with the same `DATABASE_URL`.
3. Verify readiness and the pack read/search smoke path before restoring traffic.

No pack state lives in process memory in PostgreSQL mode. Memory mode is explicitly non-durable and
must never be used for staging or production.

## Data integrity checks after recovery

```sql
select count(*) from evidence_retrieval_pack;
select id, claim, payload->>'snapshot_id', payload->>'index_version'
from evidence_retrieval_pack order by created_at desc limit 5;
select count(*) from shared_event_outbox where status = 'pending';
```

- A pack's `snapshot_id` and `index_version` must match an existing corpus snapshot/manifest.
- Pending outbox backlog means the relay is not dispatching; replay is safe (handlers key on
  `event_id`).
- If pack counts are lower than expected, restore again rather than accepting partial evidence.

## Communication

Single operator (hackathon prototype): record timeline, cause, achieved RTO/RPO and follow-up in the
project workpad. Notify the jury-facing owner before a demo if recovery lost packs or index state.
