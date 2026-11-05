# Disaster Recovery Plan — ClaimValidation

Canonical architecture: `.pi/architecture/modules/claim-validation.md`.
Runtime decision: `.pi/architecture/decisions/ADR-012-claim-validation-runtime-integration.md`.

## Scope and targets

ClaimValidation owns verified/contradicted/unsupported/ambiguous claim records, authoritative
reference figures and contradiction findings. It is durable in PostgreSQL mode via migration
`0301_claim_validation`; memory mode is non-durable and local/test only.

| Scenario | RTO | RPO | Basis |
|---|---|---|---|
| API process crash | 5 min | 0 | PostgreSQL commits per use case |
| Bad deploy | 5 min | 0 | previous image + same schema |
| Corrupt/missing claim tables | 30 min | ≤ 24 h | database backup/PITR |
| Reference-figure mistake | 10 min | 0 | register corrected figure, re-verify |
| Region loss | out of scope | — | single-region prototype |

## Backup strategy

| What | How | Frequency | Retention |
|---|---|---|---|
| `claim_validation_claim` | `pg_dump` / PITR | daily full + WAL | 30 days |
| `claim_validation_reference_figure` | `pg_dump` / PITR | daily full + WAL | 30 days |
| `claim_validation_contradiction` | `pg_dump` / PITR | daily full + WAL | 30 days |
| Code + migrations | git | per commit | permanent |
| Proofing output | CI artifact | per PR | 30 days |

## Restore procedure

1. Restore the repository at the last known-good commit and deploy the previous image if needed.
2. Restore the database from the latest dump/PITR target.
3. `uv run alembic upgrade head`; confirm `alembic current` reports `0301_claim_validation`.
4. Start one API instance.
5. `GET /healthz` → 200; `GET /readyz` → `claim_validation=ok`,
   `claim_validation_persistence` matches the configured family.
6. Integrity checks:
   ```sql
   select count(*) from claim_validation_claim;
   select count(*) from claim_validation_reference_figure;
   select count(*) from claim_validation_contradiction;
   select verdict, count(*) from claim_validation_claim group by verdict;
   ```
7. Spot-check one known claim via `GET /api/v1/claims/{id}` and one reference figure via
   `GET /api/v1/reference-figures`.
8. Re-verify any claim whose reference figure was restored/changed; do not hand-edit verdicts.
9. Record achieved RTO/RPO and root cause.

## Failover

Single API process. Start a replacement against the same database; no in-process state is required.
If the database is unavailable, do **not** switch production to memory persistence: it is refused
outside `ENV=local` and would silently lose verdict history.

## Integrity checks after recovery

```bash
curl -s localhost:8000/readyz | jq '.checks.claim_validation, .checks.claim_validation_persistence'
curl -s localhost:8000/api/v1/reference-figures | jq '.items | length'
curl -s localhost:8000/api/v1/contradictions | jq '.items | length'
```

- A claim must never be `VERIFIED` for causal/qualitative types.
- A press-tier reference figure must not exist.
- An empty reference table is valid but means quantitative claims are `AMBIGUOUS`.

## Communication

Single prototype operator: record timeline, cause, achieved RTO/RPO and follow-up. Notify the demo
owner if a restore loses claim history. Do not present reconstructed verdicts as original audited
records.
