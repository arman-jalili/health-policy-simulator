---
guardian_issue:
  id: "ISSUE-GOVERNANCE-COMPLIANCE-5"
  epic: "TBD"
  component: "Determinism"
  module: "governance-compliance"
  status: planned
  priority: high
  dependencies:
    - "none"

  in_scope:
    - "Same input + same rule version yields the identical verdict (no model call in path)"

  out_of_scope:
    - Changes to upstream components (none)
    - UI/frontend changes
    - Deployment pipeline configuration

  canonical_references:
    - module: ".pi/architecture/modules/governance-compliance.md"
    - acceptance_criteria: ".pi/architecture/modules/governance-compliance.md#acceptance-criteria"

  acceptance_criteria:
    - "Same input + same rule version yields the identical verdict (no model call in path)"

  validators:
    - ci
    - tests
    - security
    - architecture
    - canonical

  implementation_notes: |
    Read .pi/architecture/modules/governance-compliance.md BEFORE implementing.
    All Acceptance Criteria in that file must be satisfied before this issue is closed.
    Component focus: Determinism.
    CONCRETE IMPLEMENTATIONS MUST BE CREATED — interface stubs from the contract freeze
    are not sufficient. Each domain service/aggregate needs a concrete .impl.py file.

  file_changes:
    - "create: src/governance-compliance/domain/"
    - "create: src/governance-compliance/application/"
    - "create: src/governance-compliance/infrastructure/"
    - "modify: src/governance-compliance/interfaces/"
    -     - "update: tests/ (failing tests already generated — make them pass)"
---

# ISSUE-GOVERNANCE-COMPLIANCE-5: Implement Determinism — governance-compliance

## Intent

Implement **Determinism** for the `governance-compliance` module.

> ⚠️ **Read before implementing:** `.pi/architecture/modules/governance-compliance.md`
> Every item in the **Acceptance Criteria** section of that file must be satisfied
> before this issue is closed — including adapter, mapper, and WireMock items.

## Architecture Context

- **Module:** governance-compliance
- **Component:** Determinism
- **Status:** planned
- **Dependencies:** none

## In Scope (this component)

- Same input + same rule version yields the identical verdict (no model call in path)

## Acceptance Criteria (this issue)

These acceptance criteria must be satisfied before this issue can be closed:

| # | Criterion | Verify In |
|---|-----------|-----------|
| 5 | Same input + same rule version yields the identical verdict (no model call in path) | unit |

## Full Module Acceptance Criteria

> All items below must pass before the **epic** is closed.
> Items may be split across multiple issues — verify your component's items before creating the MR.

| # | Component | Criterion | Verify In |
|---|-----------|-----------|-----------|
| 1 | `GC-001` | "Dr. Müller sagte…" yields verdict `rewrite` or `reject`, never `accept` | unit |
| 2 | `GC-002` | A passage with `speaker_kind == person` inside quotation marks yields `reject` | unit |
| 3 | `GC-003` | "the minister's ministry" resolves to the canonical institution name or rejects | unit |
| 4 | `GC-004` | An uncited claim presented as fact is rewritten to `unsupported`, not accepted | unit |
| 5 | Determinism | Same input + same rule version yields the identical verdict (no model call in path) | unit |
| 6 | Violation persistence | Every non-accept verdict writes exactly one violation row, no duplicates on retry | integration |
| 7 | Provenance completeness | `DisclosePositionProvenance` fails if arguments, evidence or invocation are missing | integration |
| 8 | Adversarial suite | ≥30 adversarial strings all classified correctly; suite runs in CI | CI |
| 9 | Port contract | NegotiationSession cannot persist an argument without a guard verdict | integration |
| 10 | No domain model | Module contains no aggregates/VOs per ADR-008; validator passes | architecture |
| 11 | Wiring | Renamed guard is a blocking dependency of the negotiation write path; empty allowlist aborts boot; guard works with the LLM client patched to raise | integration |

## Implementation Sequence (from module doc)

- 1. Allowlist table + loader from StakeholderModel personas
- 2. `GC-001` rule + tests with a corpus of adversarial strings
- 3. `GC-002` quotation rule using `speaker_kind`
- 4. Rewrite path + `ViolationRecord` persistence
- 5. `EnforceInstitutionOnlyOutput` port for NegotiationSession (contract test)
- 6. `DisclosePositionProvenance` assembler
- 7. REST endpoints + read models
- 8. Adversarial regression suite (≥30 cases) run in CI

## Implementation

> **Agent instructions:**
> 1. Open `.pi/architecture/modules/governance-compliance.md` — read the full Acceptance Criteria table
> 2. Identify which rows are your responsibility for **Determinism**
> 3. Create concrete implementation files (`.impl.py`) in `src/governance-compliance/` — the interface stubs from the contract freeze are NOT enough
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
