# DR plan: GovernanceCompliance

Canonical: `docs/runbook-governance-compliance.md`

## Targets

| Scenario | RTO | RPO |
|---|---:|---:|
| API instance loss | 0 (stateless guard) | 0 |
| PostgreSQL primary loss | 15 min | last committed violation/provenance row |
| Allowlist corruption | 5 min | last persona release |

## Backup and restore

1. Back up `governance_compliance_violation`, `governance_compliance_provenance` and
   `governance_compliance_allowlist` with the normal PostgreSQL backup.
2. Restore into a clean database and run `alembic upgrade head`.
3. Verify `SELECT count(*) FROM governance_compliance_violation` and that `violation_hash` is unique.
4. Rebuild the in-process allowlist from StakeholderModel personas; boot aborts if empty.

## Failover

The guard is stateless and read-only against the allowlist. Multiple API replicas share the same
PostgreSQL tables. Writes are idempotent on `violation_hash` and `(position_id, version)`, so retry
after failover is safe.

## Integrity checks

- no duplicate `violation_hash`
- every non-accept violation has `rule_id` and `rule_version`
- every provenance row has non-empty evidence, arguments and invocation ids
- `/readyz` has `governance_compliance: ok` and nine allowlist entries
