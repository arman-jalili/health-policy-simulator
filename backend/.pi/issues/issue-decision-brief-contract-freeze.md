---
guardian_issue:
  id: "ISSUE-CONTRACT-FREEZE"
  epic: "decision-brief"
  component: "Contract Freeze"
  module: "decision-brief"
  status: planned
  priority: critical
  dependencies: []

  in_scope:
    - Define public interfaces for all components in this epic
    - Define DTOs, schemas, and API contracts
    - Document event payloads and topics
    - Create interface stubs with no implementation
    - Freeze: no implementation changes without contract change

  out_of_scope:
    - Any implementation logic
    - Database schema changes
    - Infrastructure setup

  affected_layers:
    domain:
      - Interface definitions for domain services
    application:
      - Input/output DTO definitions
    api:
      - REST/event contracts

  canonical_references:
    - module: ".pi/architecture/modules/decision-brief.md"

  acceptance_criteria:
    - "All component interfaces defined as stubs (TODO bodies)"
    - "DTO schemas documented with field names and types"
    - "API contracts frozen and reviewed"
    - "Implementation PRs reference these contracts"

  validators:
    - architecture
    - canonical

  implementation_notes: |
    Define the contract before any implementation. Every implementation issue
    depends on this contract being frozen first. The contract should include:
    interfaces, types, DTOs, event schemas, API paths, error formats.

  file_changes:
    - "create: src/decision-brief/domain/"
    - "create: src/decision-brief/application/"
    - "create: src/decision-brief/infrastructure/"
    - "create: src/decision-brief/interfaces/"
---

# Contract Freeze: decision-brief

## Intent

Define and freeze all public interfaces, contracts, and schemas for the decision-brief
epic before any implementation begins. This prevents architecture drift — implementation
must satisfy contracts, not the other way around.

## Included Components

- Aggregate root — DecisionBrief
- Entities and value objects
- Service classification
- Eight sections
- Citation gate
- Rejected proposals
- Disclaimer
- Statement evidence
- Immutability
- Lineage
- Reproduction
- Blocked outcome honesty
- Probabilistic disclaimer
- Wiring

## What Must Be Frozen

### Interfaces
- Service interfaces for every component
- Repository/DAO interfaces
- Factory interfaces

### Contracts
- Input/output DTO schemas
- API endpoint contracts (method, path, request/response)
- Event payload schemas
- Error response formats

### Out of Bounds (no contracts needed)
- Internal implementation details
- Database column names (hidden behind repository)
- Framework-specific annotations

## Acceptance Criteria

| # | Criterion | How to Verify |
|---|-----------|---------------|
| 1 | All component interfaces defined as stubs (TODO bodies) | Check src/<module>/domain/ and application/ |
| 2 | Contracts reviewed and frozen | PR approval |
| 3 | DTO schemas documented with field names and types | OpenAPI / record types |
| 4 | Implementation depends on contracts | No implementation without interface |

## Full Module Acceptance Criteria (for reference)

> These are the complete ACs for the module. The contract freeze must define the interfaces
> so every row below can be implemented in subsequent issues.

| # | Component | Criterion | Verify In |
|---|-----------|-----------|-----------|
| 1 | Eight sections | Publishing with 7 sections raises `IncompleteBrief` naming the missing kind | unit |
| 2 | Citation gate | An unresolved citation blocks publication and emits `CitationResolutionFailed` | unit + integration |
| 3 | Rejected proposals | A run with ≥1 rejected proposal whose brief omits it raises `DisclosureMissing` | unit |
| 4 | Disclaimer | A brief without disclaimer cannot publish | unit |
| 5 | Statement evidence | A statement marked `evidenced` with no citation raises `StatementWithoutCitation` | unit |
| 6 | Immutability | Mutating a published brief raises; a new version is required | unit |
| 7 | Lineage | `VersionDecisionBrief` produces version N+1 referencing N with a reason | integration |
| 8 | Reproduction | Regenerating from the run log yields identical sections except narrative wording | integration |
| 9 | Blocked outcome honesty | A veto-blocked topic renders as blocked, never as a recommendation | integration |
| 10 | Probabilistic disclaimer | Brief JSON contains the disclaimer and the model/prompt version reference | API contract |
| 11 | Wiring | Router registered; unwired provenance port blocks publication (gate cannot be skipped); `briefs:publish` enforced with 403 for analyst | integration |

## Full Implementation Sequence (for reference)

- 1. `SectionKind`, `EvidenceStatus`, `CitedStatement`, `CitationReference` VOs
- 2. `DecisionBrief.publish()` gates with incomplete-citation-disclosure tests
- 3. Projection builder for sections 1–4 from run history
- 4. Sections 5–8 from `ConsensusView`
- 5. Citation resolver against EvidenceCorpus port
- 6. Rejected-proposal disclosure wiring
- 7. `VersionDecisionBrief` lineage
- 8. Renderer JSON; REST routers + contract tests



## Implementation

> **Agent:** Create interface-only files. No implementation. Use Clean Architecture layers:
> 1. Read the architecture module to understand each component's role
> 2. Place domain interfaces in domain/, service interfaces in application/, DTOs in application/
> 3. Controllers/routers are CONCRETE — they do NOT get interfaces. The concrete router/handler class goes directly in interfaces/http/ without a separate contract file.
> 4. Event schemas go in domain/event/
> 5. Repository interfaces go in infrastructure/repository/
>
> The goal is a reviewed, frozen contract that implementation issues can depend on.
