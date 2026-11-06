# Runbook: GovernanceCompliance

Canonical module: `.pi/architecture/modules/governance-compliance.md`
Contract: `docs/contracts-governance-compliance.md`

## Startup

1. `PERSISTENCE=postgres`, `DATABASE_URL` exported.
2. `alembic upgrade head` applies `0305_governance_compliance`.
3. Boot loads the nine StakeholderModel institutions into the allowlist. Empty, duplicate or
   person-shaped entries abort construction.
4. `/readyz` reports `governance_compliance: ok`, `governance_allowlist: 9`,
   `governance_provenance: wired` and `governance_provenance_producer: close_round`.

## Failure modes

| Symptom | Cause | Action |
|---|---|---|
| Boot `ALLOWLIST_EMPTY` | StakeholderModel published no institutions | Fix personas/allowlist; do not start |
| Boot `ALLOWLIST_CONTAINS_PERSON` | Person title in a canonical name | Correct the persona; restart |
| `GOVERNANCE_GUARD_UNAVAILABLE` | Container not mounted | Fix composition; writes must fail closed |
| `GUARD_VERDICT_REQUIRED` | Write attempted without a verdict | Route the write through the guard |
| `PROVENANCE_INCOMPLETE` | Evidence, arguments or invocation missing | Take the turn that supplies the invocation, then close the round again; disclosure runs on close |
| Duplicate violation row | Bypass of `violation_hash` | Use `RecordGovernanceViolation` |
| Guard latency spike | regex/allowlist resolver (no model, no network) | Check `governance_guard_checks_total`; the guard is local and deterministic — a spike means CPU/GC, not a provider |

## Metrics

- `governance_guard_checks_total{decision}`
- `governance_violations_total{class}`
- `governance_provenance_disclosures_total`

## Rollback

`alembic downgrade 0304_simulation_pause_reason` removes the three governance tables. The guard
router and container can be removed without affecting other contexts. Never treat an empty
allowlist as permit-all during rollback.

## Verification

```bash
curl -X POST /api/v1/governance/check -H 'X-API-Key: …' \
  -d '{"text":"Dr. Müller sagte …","speaker_kind":"institution","invocation_id":"inv_1"}'
# decision is rewrite or reject, never accept
```
