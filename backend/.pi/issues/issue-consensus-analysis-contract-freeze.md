---
guardian_issue:
  id: "ISSUE-CONTRACT-FREEZE"
  epic: "consensus-analysis"
  component: "Contract Freeze"
  module: "consensus-analysis"
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
    - module: ".pi/architecture/modules/consensus-analysis.md"

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
    - "create: src/consensus-analysis/domain/"
    - "create: src/consensus-analysis/application/"
    - "create: src/consensus-analysis/infrastructure/"
    - "create: src/consensus-analysis/interfaces/"
---

# Contract Freeze: consensus-analysis

## Intent

Define and freeze all public interfaces, contracts, and schemas for the consensus-analysis
epic before any implementation begins. This prevents architecture drift — implementation
must satisfy contracts, not the other way around.

## Included Components

- Aggregate root — ConsensusRecord
- Entities and value objects
- Service classification
- Veto precedence
- Threshold
- History assertion
- Rebibuildability
- Unbacked estimate
- Assumed label
- Illustrative-value guard
- Minority capture
- Rejected proposals
- Feasibility veto check
- Comparison
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
| 1 | Veto precedence | 7/9 support for a vetoed proposal class yields `VetoBlockedOutcome`, never consensus | unit |
| 2 | Threshold | Support below threshold returns partial + minority, not consensus | unit |
| 3 | History assertion | A stance not present in the run log raises `StanceNotInHistory` | unit |
| 4 | Rebibuildability | Rebuilding projections from the run log yields byte-identical records | integration |
| 5 | Unbacked estimate | `basis=derived` with zero inputs raises and emits `UnbackedEstimateBlocked` | unit |
| 6 | Assumed label | An assumed figure persists with the label and cannot be rendered as computed | unit + API |
| 7 | Illustrative-value guard | A figure equal to a documentation example cannot be persisted as an outcome | unit |
| 8 | Minority capture | Every disapproving stakeholder appears in a recorded minority position | unit |
| 9 | Rejected proposals | Every proposal without threshold support appears in `rejected_proposals` | unit |
| 10 | Feasibility veto check | A feasible scenario naming a veto-holding institution as consenting raises | unit |
| 11 | Comparison | Alternative packages are ranked with all three dimensions present | integration |
| 12 | Wiring | Subscribed to `SimulationRunClosed`; closing a run produces consensus rows with no explicit API call; derived rows rebuild from the log | integration |

## Full Implementation Sequence (for reference)

- 1. `SupportLevel`, `ConsensusThreshold`, `VetoBlockedOutcome`, `UnresolvedConflict` VOs
- 2. `ConsensusRecord.determine` with veto precedence + history assertion
- 3. `DeriveConsensus` projection from the run log + rebuild-from-log test
- 4. `CompromisePackage` + compatibility rules + rejected-proposal capture
- 5. `EstimateBasis`, `DerivationInput`, `EstimateLimitation` + `EstimateValidator`
- 6. `Scenario` + `AssessImpact` (no LLM first: modelled figures only)
- 7. `FeasibilityRating` + veto-aware feasibility check
- 8. `CompareScenarios` ranking
- 9. REST routers + contract tests



## Implementation

> **Agent:** Create interface-only files. No implementation. Use Clean Architecture layers:
> 1. Read the architecture module to understand each component's role
> 2. Place domain interfaces in domain/, service interfaces in application/, DTOs in application/
> 3. Controllers/routers are CONCRETE — they do NOT get interfaces. The concrete router/handler class goes directly in interfaces/http/ without a separate contract file.
> 4. Event schemas go in domain/event/
> 5. Repository interfaces go in infrastructure/repository/
>
> The goal is a reviewed, frozen contract that implementation issues can depend on.
