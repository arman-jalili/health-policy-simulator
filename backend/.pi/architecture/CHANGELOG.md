# Architecture Change Log

<!--
Canonical Reference: .pi/architecture/CHANGELOG.md
Blueprint Source: Guardian Framework v1.2
DO NOT EDIT GENERATED FILES - Modify this source only
-->

This document tracks all architecture changes requiring implementation updates.

---

## Change Log Format

Each entry follows this structure:

```markdown
## [YYYY-MM-DD] - [Change Title]

### Changed
- Module: [module-name]
  - [Component]: [what changed]
  - [Component]: [what changed]

### Impact Analysis
- Files affected:
  - src/[path1]
  - src/[path2]
- Canonical refs to update:
  - .pi/architecture/modules/[module].md#[section]
- Validators required:
  - [validator-name]

### Migration Steps
1. [Step 1]
2. [Step 2]
3. [Step 3]

### Status
- [ ] Architecture doc updated
- [ ] CHANGELOG entry added
- [ ] Implementation updated
- [ ] Canonical refs updated
- [ ] Validators run
```

---

## Entries

## [2026-11-05] - IdentityAccess implemented and wired (epic #30, issues #31-#44)

### Changed
- Module: identity-access — contract frozen (#31), resolution outcomes + ACL proof (#32), strict
  anonymous rejection (#33), scope enforcement with static adapter (#34), loopback demo guard (#35),
  salted-hash key store + migration `0104` (#36), request-scoped actor attribution (#37), repo-wide
  ACL isolation (#38), admin lifecycle + immediate revocation (#39), DB/LLM readiness (#40),
  composition wiring + admin router (#41), runtime reachability + ADR-009 (#42), 81-check contract
  proofing stage + CI coverage gate (#43)
- Module: identity-access — `Status: Implemented`; every `/api/v1` route declares a scope and
  rejects unscoped principals; `demo` + `production` refuses boot
- Docs: dedicated `docs/runbook-identity-access.md` and `docs/dr-plan-identity-access.md`; ADR-009
  accepted; roadmap W1–W7 evidence recorded
- Tests: 502 passing with PostgreSQL; wired E2E covers admin issue → operator read → revoke → 401

### Impact Analysis
- Files affected:
  - `src/identity_access/**`, `src/shared/{app,config,attribution,outbox}.py`
  - `migrations/versions/0104_identity_access.py`
  - `.pi/scripts/ci/{check_identity-access_contracts,stage_identity-access_proofing,run_hardening_stages}.sh`
  - `.github/workflows/ci.yml`, `docs/`, `tests/{unit,integration}/...`
- Canonical refs to update:
  - `.pi/architecture/modules/identity-access.md#frozen-contracts-2026-11-05`
- Validators required:
  - ci, tests, security, architecture, canonical, operations, runtime-wiring, readiness

### Migration Steps
1. `alembic upgrade head` (applies `0104_identity_access`)
2. Bootstrap an admin key; issue role keys; verify `/readyz` and a scoped route
3. Keep `AUTH_MODE=strict` outside local; demo remains loopback-only

### Status
- [x] Architecture doc updated
- [x] CHANGELOG entry added
- [x] Implementation updated (#31-#44)
- [x] Canonical refs updated
- [x] Validators run

## [2026-11-05] - IdentityAccess contract frozen (issue #31)

### Changed
- Module: identity-access — froze the ACL (`Role`, `Scope`, `ROLE_SCOPES`, `ActorId`,
  `ResolutionState`, `Principal`), DTOs (`ResolutionOutcome`, key lifecycle records, readiness
  records), error codes (`UNAUTHENTICATED`, `SCOPE_REQUIRED`, `API_KEY_NOT_FOUND`), ports
  (`PrincipalPort`, `ApiKeyAdminPort`, `ReadinessPort`, `DemoModePolicy`), key-store contracts,
  admin route shapes and the composition container
- Module: identity-access — adapter-depth placement: the contract lives in `interfaces/` and is
  implemented in `infrastructure/`; `domain/` and `application/` stay empty markers because the
  ADR-008 machine projection forbids modules there
- Tests: replaced the generated placeholder files with frozen-contract assertions for all ten
  components (25 tests)

### Impact Analysis
- Files affected:
  - `src/identity_access/**`
  - `tests/unit/identity-access/**`
- Canonical refs to update:
  - `.pi/architecture/modules/identity-access.md#frozen-contracts-2026-11-05`
- Validators required:
  - architecture, canonical, ci

### Migration Steps
1. Review and approve the frozen contract (PR)
2. Implement issues #32–#41 against these names; do not reshape them without a contract change
3. Apply migration `0104_identity_access` in the key-store issue

### Status
- [x] Architecture doc updated
- [x] CHANGELOG entry added
- [x] Implementation stubs updated (contract only; bodies remain TODO)
- [x] Canonical refs updated
- [x] Validators run

## [2026-11-05] - EvidenceCorpus wiring completed (issue #26, 276c4cc)

### Changed
- Module: evidence-corpus — composition root selects adapters from `PERSISTENCE` (postgres default,
  memory explicit and local-only); `UnitOfWork` gives each request one ambient transaction;
  SQLAlchemy adapters cover document, article, passage, ingestion-run and snapshot ports
- Module: evidence-corpus — migrations `0101` (document/publication/article/passage) and `0103`
  (snapshot/snapshot_document/ingestion_run); `0102` keeps the index tables
- Module: evidence-corpus — `OutboxEventPublisher` writes drained events in the aggregate
  transaction; the lifespan `OutboxRelay` drains `shared_event_outbox` with `FOR UPDATE SKIP
  LOCKED` and marks rows dispatched (at-least-once)
- Module: evidence-corpus — `_not_implemented` residue removed; `Document.drain_events()` now drains
  article-level events; `IngestDocument` re-reads the aggregate so `citable` is current
- Roadmap: EvidenceCorpus satisfies the W1–W7 wiring definition of done (IdentityAccess remains)

### Impact Analysis
- Files affected:
  - `src/shared/{app,config,db,enums,relay}.py`
  - `src/evidence_corpus/{composition.py,infrastructure/**,interfaces/http/**}`
  - `migrations/versions/0101_evidence_corpus_documents.py`, `0103_evidence_corpus_snapshots.py`
  - `tests/unit/evidence_corpus/test_wiring.py`, `tests/integration/test_corpus_persistence.py`
- Canonical refs to update:
  - `.pi/architecture/modules/evidence-corpus.md#wiring-contract`
- Validators required:
  - ci, tests, architecture, security, operations, integration, canonical

### Migration Steps
1. Deploy with `PERSISTENCE=postgres` and run `alembic upgrade head` (applies `0101`, `0103`)
2. Verify the relay drains `shared_event_outbox` and a restart preserves documents and passages
3. Use `PERSISTENCE=memory` only for tests and a database-less local demo

### Status
- [x] Architecture doc updated
- [x] CHANGELOG entry added
- [x] Implementation updated (276c4cc)
- [x] Canonical refs updated
- [x] Validators run

## [2026-11-05] - Wiring Contracts (post-implementation audit)

### Changed
- Module: all 10 — added `## Wiring Contract` section (router registration, settings-driven composition, migrations, outbox, cross-context ports, fail-closed behaviour) and a `Wiring` acceptance criterion row per module
- Module: evidence-corpus — wiring contract marks the baseline; audit found persistence/outbox/migrations unwired (issue #26)
- Roadmap: added `## Cross-Cutting: Wiring Definition of Done` (gates W1–W7) and a per-issue DoD template; Phase 1 explicitly not closable while #26 is open

### Impact Analysis
- Files affected:
  - `.pi/architecture/modules/*.md` (10)
  - `.pi/architecture/implementation-roadmap.md`
  - implementation follow-up: `src/shared/app.py`, `src/evidence_corpus/composition.py`, `migrations/versions/`
- Canonical refs to update:
  - `.pi/architecture/modules/[module].md#wiring-contract`
- Validators required:
  - architecture, canonical, ci

### Migration Steps
1. Close issue #26 (persistence adapters, outbox publisher, migrations `0101`/`0103`)
2. Add the boot test that fails when a context router is removed from `create_app`
3. Add the architecture test forbidding cross-context repository imports
4. Apply the W1–W7 checklist to every subsequent module issue before merge

### Status
- [x] Architecture doc updated
- [x] CHANGELOG entry added
- [x] Implementation updated (issue #26 wired in 276c4cc)
- [x] Canonical refs updated
- [x] Validators run

## [2026-11-05] - Complete Architecture Package (ADR-001…ADR-008)

### Changed
- ADR-001: reviewed and accepted; explicit layer-isolation, layer-direction and transaction-ownership rules added; alternatives table expanded
- ADR-002…ADR-008: created (data storage, cross-context communication, API design, auth, cost metering, compliance engine, proportional modeling depth)
- Module: evidence-corpus — `Document` + `IngestionRun` aggregates (behavior methods, 7 invariants, Python repository protocol); Python stubs replace Rust/SQLx stubs; 12 triaged domain events with payloads; 8 endpoints; 17 glossary terms; 12 acceptance criteria
- Module: evidence-retrieval — `EvidencePack` aggregate with freeze/absence semantics; `RetrievalQuery` demoted to value object; 8 invariants; 3 triaged events; 5 endpoints; absence-finding contract; 11 acceptance criteria
- Module: stakeholder-model — `Stakeholder` + `AgentBinding` aggregates; `MandateSource` grounding and `AttributionStrength`; 10 invariants; 11 triaged events; 8 endpoints; 11 acceptance criteria
- Module: negotiation-session — `SimulationRun` aggregate with 15 owned concepts; `RoundLearning`/`LearningApplication` (negotiation-learning requirement); 14 invariants; 15 triaged events; 12 endpoints; replay-equivalence criterion
- Module: consensus-analysis — `ConsensusRecord`/`CompromisePackage`/`Scenario` aggregates; veto precedence over threshold; `EstimateBasis` provenance; 11 invariants; 9 triaged events; 7 endpoints
- Module: decision-brief — `DecisionBrief` as projection-with-identity; publication gate; `CitedStatement` and rejected-proposal disclosure; 8 invariants; 5 triaged events; 5 endpoints
- Module: claim-validation — `Claim` aggregate with claim-type verification paths; tolerance bands; `ReferenceFigure` grounding; 10 invariants; 10 triaged events; 7 endpoints
- Module: governance-compliance (service depth) — two-stage guard, 5 rules `GC-001…GC-005`, persistence contract, 5 endpoints; no aggregates introduced
- Module: simulation-orchestration (service depth) — job/invocation/progress persistence contract, budget guard, SSE replay, graph-purity rule; no aggregates introduced
- Module: identity-access (adapter depth) — `PrincipalPort` ACL, key+scope table, demo-mode guard; no aggregates introduced
- Diagrams: `system-context.md` rebuilt (actors, contexts, context map, integrations); `event-flow.md` created (event classes, delivery guarantees, explicit non-events)
- Roadmap: six phases (Bootstrap + 5), 10 modules, migrations `0000`–`0502`, effort estimates, milestones, documented orchestration/negotiation cycle

### Impact Analysis
- Files affected:
  - `.pi/architecture/decisions/ADR-001…ADR-008` (8 files)
  - `.pi/architecture/diagrams/system-context.md`, `.pi/architecture/diagrams/event-flow.md`
  - `.pi/architecture/modules/*.md` (10 module docs)
  - `.pi/architecture/implementation-roadmap.md`
  - `.pi/architecture/CHANGELOG.md`
  - (implementation, not yet created) `src/<context>/domain|application|infrastructure|interfaces/`
- Canonical refs to update:
  - `.pi/architecture/modules/[module].md` — all sections regenerated
  - `.pi/domain/ubiquitous-language.md` — unchanged; module UL sections are subsets of the 80 canonical terms
- Validators required:
  - architecture (layer isolation, depth per ADR-008)
  - canonical (doc ↔ code sync once implementation starts)
  - ci

### Migration Steps
1. Review ADR-002's explicit language deviation (SQLx → SQLAlchemy/asyncpg) and confirm the Python baseline
2. Confirm the documented `SimulationOrchestration ↔ NegotiationSession` cycle resolution before Phase 3 starts
3. Seed palette: 9 persona YAMLs (Phase 2) and ~10 authoritative `ReferenceFigure` rows (Phase 3)
4. Begin Phase 0 bootstrap; do not create context folders before their build phase

### Status
- [x] Architecture doc updated
- [x] CHANGELOG entry added
- [ ] Implementation updated (no code in this package by design)
- [ ] Canonical refs updated (pending first implementation)
- [ ] Validators run

<!-- Add new entries above this line -->

---

## Template Usage

When making architecture changes:

1. **Before change**: Review existing architecture docs
2. **During change**: Update `.pi/architecture/modules/[module].md`
3. **After change**: Add entry to this CHANGELOG
4. **Implementation**: Follow migration steps, update canonical refs
5. **Validation**: Run `validate-canonical.sh` to verify sync

---

## Architecture Sync Status

Track which changes have been synced to implementation:

| Date | Change | Module | Sync Status | Validator Status |
|------|--------|--------|-------------|------------------|
| 2026-11-05 | EvidenceCorpus wiring completed (276c4cc) | evidence-corpus | complete | pass |
| 2026-11-05 | Complete architecture package | evidence-corpus | complete | pass |
| 2026-11-05 | Complete architecture package | evidence-retrieval | pending | not run |
| 2026-11-05 | Complete architecture package | stakeholder-model | pending | not run |
| 2026-11-05 | Complete architecture package | negotiation-session | pending | not run |
| 2026-11-05 | Complete architecture package | consensus-analysis | pending | not run |
| 2026-11-05 | Complete architecture package | decision-brief | pending | not run |
| 2026-11-05 | Complete architecture package | claim-validation | pending | not run |
| 2026-11-05 | Complete architecture package | governance-compliance | pending | not run |
| 2026-11-05 | Complete architecture package | simulation-orchestration | pending | not run |
| 2026-11-05 | IdentityAccess implemented (#31-#44) | identity-access | complete | pass |
| 2026-11-05 | IdentityAccess contract freeze (#31) | identity-access | contract frozen | pass |
| 2026-11-05 | Complete architecture package | identity-access | complete | pass |

---

*Last updated: 2026-11-05*
*Framework version: 1.2.0*

## 2026-11-05 — EvidenceCorpus implemented

- Contract frozen (values, entities, events, errors, ports, DTOs, API surface) and then implemented
  component by component: entities/invariants, value-object validation, domain rules, extraction
  (native + OCR), segmentation strategies, authority classification, canonical linking, snapshot
  pinning, PostgreSQL `tsvector` indexing, and the HTTP surface.
- Migrations: `0102_evidence_corpus_index` (indexed passages + index manifest).
- Proofing: `.pi/scripts/ci/check_evidence_corpus_contract.py` verifies routes, enums, rubric, event
  payloads, error codes, port implementations and invariants; wired into CI and the hardening stages.
- Observability: `GET /metrics` (Prometheus text) with request, duration and domain-event counters.
- Known deferral: document/article/passage persistence is in-memory; SQLAlchemy adapters are stubs.
