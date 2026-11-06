---
guardian_issue:
  id: "ISSUE-CONSENSUS-ANALYSIS-3"
  epic: "TBD"
  component: "Service classification"
  module: "consensus-analysis"
  status: planned
  priority: high
  dependencies:
    - "none"

  in_scope:
    - "7/9 support for a vetoed proposal class yields `VetoBlockedOutcome`, never consensus"
    - "Support below threshold returns partial + minority, not consensus"
    - "A stance not present in the run log raises `StanceNotInHistory`"

  out_of_scope:
    - Changes to upstream components (none)
    - UI/frontend changes
    - Deployment pipeline configuration

  canonical_references:
    - module: ".pi/architecture/modules/consensus-analysis.md"
    - acceptance_criteria: ".pi/architecture/modules/consensus-analysis.md#acceptance-criteria"

  acceptance_criteria:
    - "7/9 support for a vetoed proposal class yields `VetoBlockedOutcome`, never consensus"
    - "Support below threshold returns partial + minority, not consensus"
    - "A stance not present in the run log raises `StanceNotInHistory`"

  validators:
    - ci
    - tests
    - security
    - architecture
    - canonical

  implementation_notes: |
    Read .pi/architecture/modules/consensus-analysis.md BEFORE implementing.
    All Acceptance Criteria in that file must be satisfied before this issue is closed.
    Component focus: Service classification.
    CONCRETE IMPLEMENTATIONS MUST BE CREATED — interface stubs from the contract freeze
    are not sufficient. Each domain service/aggregate needs a concrete .impl.py file.

  file_changes:
    - "create: src/consensus-analysis/domain/"
    - "create: src/consensus-analysis/application/"
    - "create: src/consensus-analysis/infrastructure/"
    - "modify: src/consensus-analysis/interfaces/"
    -     - "update: tests/ (failing tests already generated — make them pass)"
---

# ISSUE-CONSENSUS-ANALYSIS-3: Implement Service classification — consensus-analysis

## Intent

Implement **Service classification** for the `consensus-analysis` module.

> ⚠️ **Read before implementing:** `.pi/architecture/modules/consensus-analysis.md`
> Every item in the **Acceptance Criteria** section of that file must be satisfied
> before this issue is closed — including adapter, mapper, and WireMock items.

## Architecture Context

- **Module:** consensus-analysis
- **Component:** Service classification
- **Status:** planned
- **Dependencies:** none

## In Scope (this component)

- 7/9 support for a vetoed proposal class yields `VetoBlockedOutcome`, never consensus
- Support below threshold returns partial + minority, not consensus
- A stance not present in the run log raises `StanceNotInHistory`

## Acceptance Criteria (this issue)

These acceptance criteria must be satisfied before this issue can be closed:

| # | Criterion | Verify In |
|---|-----------|-----------|
| 1 | 7/9 support for a vetoed proposal class yields `VetoBlockedOutcome`, never consensus | unit |
| 2 | Support below threshold returns partial + minority, not consensus | unit |
| 3 | A stance not present in the run log raises `StanceNotInHistory` | unit |

## Full Module Acceptance Criteria

> All items below must pass before the **epic** is closed.
> Items may be split across multiple issues — verify your component's items before creating the MR.

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

## Implementation Sequence (from module doc)

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

> **Agent instructions:**
> 1. Open `.pi/architecture/modules/consensus-analysis.md` — read the full Acceptance Criteria table
> 2. Identify which rows are your responsibility for **Service classification**
> 3. Create concrete implementation files (`.impl.py`) in `src/consensus-analysis/` — the interface stubs from the contract freeze are NOT enough
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
