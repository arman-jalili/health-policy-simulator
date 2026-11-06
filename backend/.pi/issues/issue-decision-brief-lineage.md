---
guardian_issue:
  id: "ISSUE-DECISION-BRIEF-10"
  epic: "TBD"
  component: "Lineage"
  module: "decision-brief"
  status: planned
  priority: high
  dependencies:
    - "none"

  in_scope:
    - "`VersionDecisionBrief` produces version N+1 referencing N with a reason"

  out_of_scope:
    - Changes to upstream components (none)
    - UI/frontend changes
    - Deployment pipeline configuration

  canonical_references:
    - module: ".pi/architecture/modules/decision-brief.md"
    - acceptance_criteria: ".pi/architecture/modules/decision-brief.md#acceptance-criteria"

  acceptance_criteria:
    - "`VersionDecisionBrief` produces version N+1 referencing N with a reason"

  validators:
    - ci
    - tests
    - security
    - architecture
    - canonical

  implementation_notes: |
    Read .pi/architecture/modules/decision-brief.md BEFORE implementing.
    All Acceptance Criteria in that file must be satisfied before this issue is closed.
    Component focus: Lineage.
    CONCRETE IMPLEMENTATIONS MUST BE CREATED — interface stubs from the contract freeze
    are not sufficient. Each domain service/aggregate needs a concrete .impl.py file.

  file_changes:
    - "create: src/decision-brief/domain/"
    - "create: src/decision-brief/application/"
    - "create: src/decision-brief/infrastructure/"
    - "modify: src/decision-brief/interfaces/"
    -     - "update: tests/ (failing tests already generated — make them pass)"
---

# ISSUE-DECISION-BRIEF-10: Implement Lineage — decision-brief

## Intent

Implement **Lineage** for the `decision-brief` module.

> ⚠️ **Read before implementing:** `.pi/architecture/modules/decision-brief.md`
> Every item in the **Acceptance Criteria** section of that file must be satisfied
> before this issue is closed — including adapter, mapper, and WireMock items.

## Architecture Context

- **Module:** decision-brief
- **Component:** Lineage
- **Status:** planned
- **Dependencies:** none

## In Scope (this component)

- `VersionDecisionBrief` produces version N+1 referencing N with a reason

## Acceptance Criteria (this issue)

These acceptance criteria must be satisfied before this issue can be closed:

| # | Criterion | Verify In |
|---|-----------|-----------|
| 7 | `VersionDecisionBrief` produces version N+1 referencing N with a reason | integration |

## Full Module Acceptance Criteria

> All items below must pass before the **epic** is closed.
> Items may be split across multiple issues — verify your component's items before creating the MR.

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

## Implementation Sequence (from module doc)

- 1. `SectionKind`, `EvidenceStatus`, `CitedStatement`, `CitationReference` VOs
- 2. `DecisionBrief.publish()` gates with incomplete-citation-disclosure tests
- 3. Projection builder for sections 1–4 from run history
- 4. Sections 5–8 from `ConsensusView`
- 5. Citation resolver against EvidenceCorpus port
- 6. Rejected-proposal disclosure wiring
- 7. `VersionDecisionBrief` lineage
- 8. Renderer JSON; REST routers + contract tests

## Implementation

> **Agent instructions:**
> 1. Open `.pi/architecture/modules/decision-brief.md` — read the full Acceptance Criteria table
> 2. Identify which rows are your responsibility for **Lineage**
> 3. Create concrete implementation files (`.impl.py`) in `src/decision-brief/` — the interface stubs from the contract freeze are NOT enough
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
