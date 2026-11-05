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

## [2026-11-06] - SimulationOrchestration contract freeze (issue #205)

### Changed
- Module: simulation-orchestration — froze all public interfaces and schemas before implementation:
  graph sequencing ports, graph state, invocation envelope, budget/pause/retry/prompt rules,
  job/invocation/progress/prompt repository ports, progress event payloads, error codes, HTTP routes,
  published ACL views and composition factory.
- Added 40 contract-freeze checks across the 11 epic components; placeholders replaced because their
  hyphenated generated identifiers were invalid.
- Set module status to **Contract Frozen (implementation pending)** and documented the ADR-008
  service-depth exception (no domain modules; event schemas in `application/`).

### Impact Analysis
- Files affected: `src/simulation_orchestration/**`, `tests/unit/simulation-orchestration/**`,
  `tests/unit/simulation_orchestration_contract_helpers.py`, module doc
- Canonical refs: module doc `## Contract Freeze`, API/persistence tables
- Validators: unit, architecture conformance, modeling depth, canonical

### Status
- [x] All component interfaces defined as stubs
- [x] DTO/event/error contracts documented
- [x] API contract frozen with scopes and status codes
- [x] Implementation stubs depend on the frozen ports
- [x] Architecture docs updated

---

## [2026-11-06] - ClaimValidation runtime defect fixes (#200, #201, #202)

### Changed
- Measure identity: `ResolveMeasureIdentity` is now called on the verify/register/list paths;
  register responses expose the normalised dimensions; mismatches escalate with a reason naming the
  differing period/unit/geography.
- Contradictions: `VerifyClaim` calls `ContradictionDetector.finding_for` and
  `RecordContradiction.execute`; findings use a deterministic pair id and upsert.
- Number parsing: multiple candidate numbers and year-leading text return `None`; scale/unit markers
  are read from the immediate two-token window.

### Impact Analysis
- Files affected: `src/claim_validation/{application/services.py,domain/services.py,domain/claim.py,
  domain/values.py,infrastructure/number_parser.py,interfaces/http/*}`, integration/unit tests,
  proofing script
- Canonical refs: module doc runtime fixes, AC 9/10, contradiction invariant
- Validators: unit, integration, proofing (95 checks)

### Status
- [x] Public-API normalisation proof
- [x] Contradiction pipeline and idempotency proof
- [x] Parser ambiguity refusal proof
- [x] Proofing checks tightened

---

## [2026-11-06] - ClaimValidation architecture readiness (issue #181)

### Changed
- Added `docs/runbook-claim-validation.md` and `docs/dr-plan-claim-validation.md`, linked from the
  shared indexes.
- `/readyz` reports `claim_validation` and `claim_validation_persistence`; boot logs
  `claim_validation_wired`.
- Ticked the ClaimValidation-related Phase 3 ACs; documented the verification marker.
- README status/section and migration chain updated for `0301_claim_validation`.

### Impact Analysis
- Files affected: `src/shared/http/health.py`, `src/claim_validation/composition.py`, docs, roadmap
- Canonical refs: module doc, ADR-012
- Validators: readiness 9/9, architecture, canonical, operations

### Status
- [x] Runbook and DR plan
- [x] Observability fields
- [x] Roadmap ACs recorded
- [x] Readiness green

---

## [2026-11-06] - ClaimValidation runtime integration (issue #179)

### Changed
- Module: claim-validation
  - Wired the container in `shared.app` with durable PostgreSQL repositories under
    `PERSISTENCE=postgres`; memory remains the explicit test/local family.
  - Added migration `0301_claim_validation` for claims, reference figures and contradictions.
  - Added ADR-012 (Accepted) and removed the pre-wiring `NotImplementedError` bodies.
  - Added public-API and restart round-trip integration tests.

### Impact Analysis
- Files affected: `src/shared/app.py`, `src/claim_validation/**`,
  `migrations/versions/0301_claim_validation.py`, integration tests
- Canonical refs: ADR-012, module wiring contract
- Validators: migrations, integration, runtime wiring, architecture

### Status
- [x] Runtime path wired
- [x] Migration applied and reversible
- [x] ADR accepted
- [x] E2E and persistence proofs

---

## [2026-11-06] - ClaimValidation contract freeze (issue #164)

### Changed
- Module: claim-validation
  - Added the frozen domain/application/infrastructure/interfaces skeleton: values, entities,
    `Claim`, events, errors, repository ports, domain services, DTOs, published view and 7 routes.
  - Added structural contract tests for every included component.

### Impact Analysis
- Files affected: `src/claim_validation/**`, `tests/unit/claim-validation/**`
- Canonical refs: module doc, ADR-004, ADR-008
- Validators: architecture, CI, tests

### Status
- [x] Architecture doc updated
- [x] CHANGELOG entry added
- [x] Contract tests added
- [x] Stubs name their implementing issue

---

## [2026-11-06] - Phase 2 acceptance recorded (issue #141)

### Changed
- Roadmap: Phase 2 ACs 1–7 now checked with executable test references.
- Roadmap: EvidenceRetrieval deliverables corrected to prefix-aware `tsvector`/`ts_rank` lexical +
  feature-hashing dense; no BM25 or pgvector claim.
- Roadmap/module docs: `0201` recorded as the single `evidence_retrieval_pack` JSONB table;
  `0202_stakeholder_model` recorded as deferred D-001 rather than delivered.

### Impact Analysis
- Files affected: `.pi/architecture/implementation-roadmap.md`,
  `.pi/architecture/modules/{evidence-retrieval,stakeholder-model}.md`
- Canonical refs: Phase 2, D-001, ADR-010, ADR-011
- Validators: architecture, canonical, readiness

### Status
- [x] Phase 2 ACs recorded
- [x] Migration claims match the tree
- [x] Deliverable wording matches the module doc
- [x] Stale module-doc persistence entries corrected

---

## [2026-11-06] - Postgres compound lexical search (issue #140)

### Changed
- Module: evidence-retrieval
  - Lexical adapter: replaced `plainto_tsquery` with an explicit prefix `to_tsquery` built from the
    rewritten `OR` terms; filter and `ts_rank` now share one expression.
  - Memory adapter: prefix-token matching aligned with Postgres, replacing substring matching.
  - New shared parser `evidence_corpus/infrastructure/indexing/lexical.py` so adapters cannot drift.

### Impact Analysis
- Files affected:
  - `src/evidence_corpus/infrastructure/indexing/{postgres,memory,lexical}.py`
  - `tests/integration/test_index_writer.py`
  - `tests/integration/test_evidence_retrieval_hybrid_search.py`
- Canonical refs: module doc Invariant 9; Phase 2 AC 1
- Validators: integration (real PostgreSQL), ci, tests, architecture

### Status
- [x] Architecture doc updated
- [x] CHANGELOG entry added
- [x] Real-Postgres regression tests added
- [x] Adapter parity and monotone-recall tests added

---

## [2026-11-06] - StakeholderModel architecture readiness (issue #120)

### Changed
- Module: stakeholder-model
  - Added `docs/runbook-stakeholder-model.md` and `docs/dr-plan-stakeholder-model.md`, linked from
    the shared runbook/DR index.
  - Added business/technical counters for registrations, selections, bindings, positions,
    authority refusals and allowlist publications.
  - `/readyz` reports `stakeholder_model` plus the published institution count.
  - Module status set to implemented with a Runtime Integration section; README/stakeholder
    section and proofing command synced.
  - The in-memory durability limitation is explicit in the module doc, README, runbook and DR plan.

### Impact Analysis
- Files affected:
  - `src/stakeholder_model/application/services.py`
  - `src/stakeholder_model/composition.py`
  - `src/shared/http/health.py`
  - `docs/runbook-stakeholder-model.md`, `docs/dr-plan-stakeholder-model.md`
  - `README.md`, `.pi/architecture/modules/stakeholder-model.md`
- Canonical refs: module doc, ADR-011
- Validators: readiness, architecture, canonical, ci, tests, operations

### Status
- [x] Architecture doc updated
- [x] CHANGELOG entry added
- [x] Observability updated
- [x] Runbook and DR plan added
- [x] Readiness validator run

---

## [2026-11-06] - StakeholderModel runtime integration (issue #118)

### Changed
- Module: stakeholder-model
  - `shared.app` builds the stakeholder container and mounts the eight-route router.
  - Boot loads and validates all nine persona cards; invalid configuration aborts construction.
  - The institutional allowlist is published to the GovernanceCompliance guard adapter.
  - The HTTP path now exercises selection, binding, history recording and authority refusal.
  - ADR-011 records the runtime integration decision.

### Impact Analysis
- Files affected:
  - `src/shared/app.py`
  - `src/stakeholder_model/composition.py`
  - `src/stakeholder_model/interfaces/http/**`
  - `tests/integration/test_stakeholder_wiring.py`
- Canonical refs: `.pi/architecture/modules/stakeholder-model.md`, ADR-011
- Validators: architecture, canonical, ci, tests, runtime-wiring

### Status
- [x] Architecture doc updated
- [x] CHANGELOG entry added
- [x] Implementation updated
- [x] Canonical refs updated
- [x] Validators run

---

## [2026-11-06] - StakeholderModel contract freeze (issue #102)

### Changed
- Module: stakeholder-model
  - Domain: froze IDs, enums, value objects, `Stakeholder`, `StakeholderProfile`,
    `AgentBinding`, eleven event payloads, error codes, repository protocols and policy stubs.
  - Application: froze one request/result DTO per use case, transaction/clock/guard/persona ports
    and every application service signature.
  - Interfaces: froze the partner contract (`StakeholderProfileView`, `AgentBindingView`,
    `InstitutionalAllowlistView`) and the eight `/api/v1` routes with request/response schemas.
  - Stubs raise `NotImplementedError` naming the implementation issue; no behaviour was added.

### Impact Analysis
- Files affected:
  - `src/stakeholder_model/**`
  - `tests/unit/stakeholder-model/**`
- Canonical refs: `.pi/architecture/modules/stakeholder-model.md`
- Validators: architecture, canonical, ci, tests, security, operations, runtime-wiring

### Migration Steps
1. Implementation issues replace the named `NotImplementedError` bodies.
2. Contracts are additive-only; rename requires a new freeze entry.

### Status
- [x] Architecture doc updated
- [x] CHANGELOG entry added
- [x] Implementation stubs created
- [x] Canonical refs updated
- [x] Validators run

---

## [2026-11-05] - EvidenceRetrieval scores, hybrid path and trace truthfulness (issue #99)

### Changed
- Module: evidence-retrieval
  - Scoring: authority is resolved per candidate from the corpus rule and its source type;
    recency is applied per candidate with exemptions; directness is derived from claim/passage
    evidence; lexical is measured from query-term coverage; semantic is a real dense similarity.
  - Hybrid: lexical + dense rankings are fused with `ReciprocalRankFusion`, then an overlap
    reranker runs. Dense uses the vendor-free `hashing-char3gram-v1` adapter over the pinned
    snapshot; pgvector HNSW remains target-state.
  - Trace: `RetrievalTrace` records `retrieval_mode`, the actual embedding/reranker model ids and
    the snapshot's real `index_version`; the `"configured"` placeholder is gone.
  - Readiness: `/readyz` reports `evidence_retrieval_mode` and the capability detail.
  - Evaluation: a 50-claim lexical-vs-hybrid recall report is produced by
    `scripts/evaluate_retrieval.py` and uploaded by CI.
- Module: evidence-corpus
  - `PassageView` publishes the declared `source_type` so retrieval can look up the rubric.
  - Index manifests name the hashing dense model used by retrieval.

### Impact Analysis
- Files affected:
  - `src/evidence_retrieval/application/services.py`
  - `src/evidence_retrieval/domain/{entities,values,services,repositories}.py`
  - `src/evidence_retrieval/infrastructure/adapters.py`
  - `src/evidence_retrieval/composition.py`
  - `src/shared/text_embedding.py`
  - `src/evidence_corpus/domain/published.py`
  - `scripts/evaluate_retrieval.py`
- Canonical refs: `.pi/architecture/modules/evidence-retrieval.md`, ADR-010
- Validators: architecture, canonical, ci, tests, security, operations, readiness

### Migration Steps
1. No schema migration. Packs written before this change keep their recorded trace.
2. Re-index a corpus if its manifest still says `embedding_model=none` and dense retrieval is
   expected.

### Status
- [x] Architecture doc updated
- [x] CHANGELOG entry added
- [x] Implementation updated
- [x] Canonical refs updated
- [x] Validators run

## [2026-11-05] - EvidenceRetrieval architecture readiness (issue #79)

### Changed
- Module: evidence-retrieval
  - Runbook and DR plan added for pack lifecycle, readiness triage and restore.
  - Metrics: searches, candidates, packs and reweights are exposed on `/metrics`.
  - Module status moved to Implemented; runtime integration section records the entry path,
    corpus boundary, E2E proof and ADR-010.
  - README and generic runbook/DR docs link the retrieval operations.

### Impact Analysis
- Files affected:
  - `docs/runbook-evidence-retrieval.md`, `docs/dr-plan-evidence-retrieval.md`
  - `docs/runbook.md`, `docs/dr-plan.md`, `README.md`
  - `src/evidence_retrieval/application/services.py`
  - `.pi/architecture/modules/evidence-retrieval.md`
- Canonical refs: module doc and ADR-010
- Validators: readiness, canonical, architecture, operations, ci, tests, security

### Migration Steps
1. None beyond `0201_evidence_retrieval` from the wiring issue.

### Status
- [x] Architecture doc updated
- [x] CHANGELOG entry added
- [x] Implementation updated
- [x] Canonical refs updated
- [x] Validators run

## [2026-11-05] - EvidenceRetrieval runtime integration (issue #77)

### Changed
- Module: evidence-retrieval
  - Runtime entry: `shared.app.create_app` builds the retrieval container after the corpus and
    mounts the router.
  - Corpus access: `CorpusPassageSearch` consumes only published corpus ports.
  - Persistence: migration `0201_evidence_retrieval` and the SQLAlchemy JSONB pack adapter.
  - Readiness: `/readyz` reports `evidence_retrieval` and returns 503 when embeddings or reranker
    are unreachable.
  - Legacy path: none existed; pre-wiring `NotImplementedError` stubs are retired.

### Impact Analysis
- Files affected:
  - `src/shared/app.py`, `src/shared/http/health.py`
  - `src/evidence_retrieval/composition.py`, `infrastructure/adapters.py`,
    `infrastructure/repository/sqlalchemy.py`
  - `migrations/versions/0201_evidence_retrieval.py`
  - `tests/integration/test_evidence_retrieval_e2e.py`
- Canonical refs: `.pi/architecture/modules/evidence-retrieval.md`,
  `.pi/architecture/decisions/ADR-010-evidence-retrieval-runtime-integration.md`
- Validators required: tests, architecture, runtime reachability, canonical

### Migration Steps
1. Apply `alembic upgrade head` (creates `evidence_retrieval_pack`).

### Status
- [x] Architecture doc updated
- [x] CHANGELOG entry added
- [x] Implementation updated
- [x] Canonical refs updated
- [x] Validators run

## [2026-11-05] - EvidenceRetrieval contract frozen (issue #61)

### Changed
- Module: evidence-retrieval
  - Aggregate: frozen `EvidencePack` fields, one-way `freeze()`, absence and provenance guards
  - Entities: `EvidenceCandidate`, `RetrievalTrace`
  - Value objects: IDs, `StanceLabel`, `EvidenceScore`, `RecencyPolicy`, `AbsenceFinding`,
    `AuthorityWeight`, `QueryRewrite`, `RetrievalQuery`, `CoverageReport`
  - Services: domain `ScoreEvidenceCandidates`, `ApplyRecencyPolicy`, `ReciprocalRankFusion`,
    `StanceClassifier`; application search/assemble/read/reweight use cases
  - Ports: `EvidencePackRepository`, `PassageSearchPort`, embedding/reranker/rewrite/readiness/clock
  - API: five `/api/v1/evidence/*` routes with `runs:read` / `runs:write` scopes
  - Events: `EvidencePackAssembled`, `ContradictingEvidenceSurfaced`, `EvidenceAbsenceRecorded`
  - Errors: `PACK_FROZEN` (409), `ABSENCE_WITH_CONTRADICTION` (409),
    `CANDIDATE_WITHOUT_PROVENANCE` (422), `EVIDENCE_PACK_NOT_FOUND` (404)

### Impact Analysis
- Files affected:
  - `src/evidence_retrieval/domain/`
  - `src/evidence_retrieval/application/`
  - `src/evidence_retrieval/interfaces/`
  - `src/evidence_retrieval/composition.py`
  - `tests/unit/evidence-retrieval/`
- Canonical refs to update:
  - `.pi/architecture/modules/evidence-retrieval.md#contract-freeze-2026-11-05`
- Validators required: tests, architecture, modeling depth, canonical

### Migration Steps
1. None — interface-only freeze; no schema or runtime wiring yet.

### Status
- [x] Architecture doc updated
- [x] CHANGELOG entry added
- [x] Implementation unchanged (stubs only)
- [x] Canonical refs updated
- [x] Validators run

## [2026-11-05] - Phase 1 acceptance evidence recorded

### Changed
- Roadmap: all six Phase 1 acceptance criteria ticked with test references
- Test: the corpus restart round-trip now compares the passage text to the extracted source slice
  (`source_text[start:end]`), not a hand-written string
- Test: the OCR route assertion now also requires `ExtractionQuality.is_acceptable()`

### Impact Analysis
- Files affected: `.pi/architecture/implementation-roadmap.md`,
  `tests/integration/test_corpus_persistence.py`,
  `tests/unit/evidence_corpus/test_extract_document_text.py`
- Canonical refs to update: `.pi/architecture/modules/evidence-corpus.md`
- Validators required: tests, canonical, architecture

### Migration Steps
1. None — evidence and test strengthening only.

### Status
- [x] Architecture doc updated
- [x] CHANGELOG entry added
- [x] Implementation unchanged
- [x] Canonical refs unchanged
- [x] Validators run

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
