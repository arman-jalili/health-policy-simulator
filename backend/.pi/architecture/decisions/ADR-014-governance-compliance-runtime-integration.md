# ADR-014: GovernanceCompliance runtime integration

**Status:** Accepted
**Date:** 2026-11-06
**Context:** governance-compliance epic

## Decision

Wire `GovernanceCompliance` into the modular monolith as a blocking pre-persistence guard:

- `shared/app.py` builds one container from the StakeholderModel published allowlist and mounts
  `governance_compliance_router`.
- An empty or person-containing allowlist aborts construction; it is never permit-all.
- The guard chain is application-owned and deterministic. It has no LLM client; the provider
  adapters cannot be reached from `application/` (AST-enforced).
- PostgreSQL persistence uses `governance_compliance_violation`,
  `governance_compliance_provenance` and `governance_compliance_allowlist`.
- HTTP is the only public entry point; the container and published views stay framework-free.

## Consequences

- Every argument/position write can depend on `InstitutionGuard` and fail closed when unbound.
- Violations are append-only and idempotent on `violation_hash`.
- The guard remains testable with the LLM client patched to raise because it never calls it.
