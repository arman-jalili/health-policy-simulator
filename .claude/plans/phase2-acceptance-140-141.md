# Phase 2 acceptance follow-up — issues #140, #141

## Group

Related batch: #140 is the behavioural defect; #141 records the verified Phase 2 AC state and cannot
be truthful until #140 lands.

## Order

1. **#140** — fix Postgres compound lexical search:
   - add shared query-term parsing for memory/Postgres adapters
   - Postgres: OR/AND prefix tsquery, same expression for filter and `ts_rank`
   - memory: prefix-token semantics matching Postgres
   - integration tests: naive-vs-rewritten, adapter parity, monotone recall, trace
2. **#141** — update `.pi/architecture/implementation-roadmap.md` Phase 2:
   - tick ACs with test references
   - correct EvidenceRetrieval deliverables wording
   - record `0201` actual shape and `0202` as deferred D-001
   - fix stale module-doc migration claims

## Validation

- `pytest -m integration` against PostgreSQL
- full `pytest`
- ruff / format / mypy
- architecture, canonical, operations, readiness
- CI on the PR
