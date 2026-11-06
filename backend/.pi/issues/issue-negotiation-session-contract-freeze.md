---
guardian_issue:
  id: "ISSUE-CONTRACT-FREEZE"
  epic: "negotiation-session"
  component: "Contract Freeze"
  module: "negotiation-session"
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
    - module: ".pi/architecture/modules/negotiation-session.md"

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
    - "create: src/negotiation-session/domain/"
    - "create: src/negotiation-session/application/"
    - "create: src/negotiation-session/infrastructure/"
    - "create: src/negotiation-session/interfaces/"
---

# Contract Freeze: negotiation-session

## Intent

Define and freeze all public interfaces, contracts, and schemas for the negotiation-session
epic before any implementation begins. This prevents architecture drift — implementation
must satisfy contracts, not the other way around.

## Included Components

- Aggregate root — SimulationRun
- Owned entities and value objects
- Service classification
- Phase monotonicity
- Round close guard
- Revision without cause
- One open position
- Evidence requirement
- Turn discipline
- Round cap
- Coalition offer
- Learning
- Closed immutability
- Replay equivalence
- ACL purity
- SSE
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
| 1 | Phase monotonicity | Attempting `open_round` after `CLOSED` raises; phase never regresses | unit |
| 2 | Round close guard | `close_round` raises unless every bound stakeholder has a turn or an abstention | unit |
| 3 | Revision without cause | `revise_position` with a reason citing nothing emits `PositionRevisionRejected` and changes no state | unit |
| 4 | One open position | A second `submit_initial_position` for the same (stakeholder, topic) supersedes, never duplicates | unit |
| 5 | Evidence requirement | An argument with neither evidence nor an `unsupported` flag raises `ArgumentWithoutEvidence` | unit |
| 6 | Turn discipline | A duplicate turn on the same topic in one round is refused | unit |
| 7 | Round cap | With `round_cap=5`, the 6th `open_round` forces terminal evaluation | unit |
| 8 | Coalition offer | A coalition containing a stakeholder who never received an offer cannot be formed | unit |
| 9 | Learning | A round cannot close without `RoundLearning`; the next round's prompt receives it | unit + integration |
| 10 | Closed immutability | Mutating a closed run raises; `/events` still replays fully | unit |
| 11 | Replay equivalence | Folding the event log to round N equals the live state at round N | integration |
| 12 | ACL purity | No retrieval or vector types appear in `domain/` (import check) | architecture test |
| 13 | SSE | A live run emits ordered events; reconnecting with `Last-Event-ID` replays without gaps | integration |
| 14 | Wiring | Router + SSE registered; ACL ports bound to real upstream contexts; a run survives restart and `/events` replays; missing guard blocks writes (fails closed) | integration |

## Full Implementation Sequence (for reference)

- 1. Value objects: `NegotiationPhase`, `ArgumentStance`, `Proposal`, `ProposalComponent`, `RevisionReason`, `StoppingCondition`, `TurnAssignment`
- 2. `SimulationRun` skeleton + phase monotonicity tests
- 3. Round lifecycle: `open_round`, turn availability, abstention, `close_round`
- 4. `Position` with supersede semantics + revision-without-cause rejection
- 5. `Argument` + evidence requirement + unsupported flag
- 6. `ConflictTopic` tracking with stance history
- 7. `Coalition` + `CoalitionOffer` accept/decline
- 8. `RoundLearning` capture + carry-forward + `LearningApplication`
- 9. `EvaluateStoppingCondition` (consensus, cap, deadlock)
- 10. Repository + outbox + event log
- 11. ACL: `EvidencePackView` → `ClaimEvidence`; `ClaimValidation` verdict gate
- 12. REST routers + SSE publisher
- 13. `ReplaySimulationHistory` fold + equivalence test against live state



## Implementation

> **Agent:** Create interface-only files. No implementation. Use Clean Architecture layers:
> 1. Read the architecture module to understand each component's role
> 2. Place domain interfaces in domain/, service interfaces in application/, DTOs in application/
> 3. Controllers/routers are CONCRETE — they do NOT get interfaces. The concrete router/handler class goes directly in interfaces/http/ without a separate contract file.
> 4. Event schemas go in domain/event/
> 5. Repository interfaces go in infrastructure/repository/
>
> The goal is a reviewed, frozen contract that implementation issues can depend on.
