---
guardian_issue:
  id: "ISSUE-NEGOTIATION-SESSION-13"
  epic: "TBD"
  component: "Closed immutability"
  module: "negotiation-session"
  status: planned
  priority: high
  dependencies:
    - "none"

  in_scope:
    - "Mutating a closed run raises; `/events` still replays fully"

  out_of_scope:
    - Changes to upstream components (none)
    - UI/frontend changes
    - Deployment pipeline configuration

  canonical_references:
    - module: ".pi/architecture/modules/negotiation-session.md"
    - acceptance_criteria: ".pi/architecture/modules/negotiation-session.md#acceptance-criteria"

  acceptance_criteria:
    - "Mutating a closed run raises; `/events` still replays fully"

  validators:
    - ci
    - tests
    - security
    - architecture
    - canonical

  implementation_notes: |
    Read .pi/architecture/modules/negotiation-session.md BEFORE implementing.
    All Acceptance Criteria in that file must be satisfied before this issue is closed.
    Component focus: Closed immutability.
    CONCRETE IMPLEMENTATIONS MUST BE CREATED — interface stubs from the contract freeze
    are not sufficient. Each domain service/aggregate needs a concrete .impl.py file.

  file_changes:
    - "create: src/negotiation-session/domain/"
    - "create: src/negotiation-session/application/"
    - "create: src/negotiation-session/infrastructure/"
    - "modify: src/negotiation-session/interfaces/"
    -     - "update: tests/ (failing tests already generated — make them pass)"
---

# ISSUE-NEGOTIATION-SESSION-13: Implement Closed immutability — negotiation-session

## Intent

Implement **Closed immutability** for the `negotiation-session` module.

> ⚠️ **Read before implementing:** `.pi/architecture/modules/negotiation-session.md`
> Every item in the **Acceptance Criteria** section of that file must be satisfied
> before this issue is closed — including adapter, mapper, and WireMock items.

## Architecture Context

- **Module:** negotiation-session
- **Component:** Closed immutability
- **Status:** planned
- **Dependencies:** none

## In Scope (this component)

- Mutating a closed run raises; `/events` still replays fully

## Acceptance Criteria (this issue)

These acceptance criteria must be satisfied before this issue can be closed:

| # | Criterion | Verify In |
|---|-----------|-----------|
| 10 | Mutating a closed run raises; `/events` still replays fully | unit |

## Full Module Acceptance Criteria

> All items below must pass before the **epic** is closed.
> Items may be split across multiple issues — verify your component's items before creating the MR.

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

## Implementation Sequence (from module doc)

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

> **Agent instructions:**
> 1. Open `.pi/architecture/modules/negotiation-session.md` — read the full Acceptance Criteria table
> 2. Identify which rows are your responsibility for **Closed immutability**
> 3. Create concrete implementation files (`.impl.py`) in `src/negotiation-session/` — the interface stubs from the contract freeze are NOT enough
> 4. Each domain aggregate/service must have a working implementation with business logic
> 5. Verify each AC row is satisfied in `src/` before marking done
> 6. Run validators and create MR

### Steps

1. Read canonical architecture references
2. Run the pre-generated failing tests: `cd tests && pytest`
3. Verify tests FAIL (Red phase)
4. Implement domain entities and interfaces
5. Implement application service/handler
6. Add infrastructure connections
7. Run tests again — they should PASS (Green phase)
8. Refactor if needed (Refactor phase)
9. Write integration tests
10. Run all validators
11. Create MR
