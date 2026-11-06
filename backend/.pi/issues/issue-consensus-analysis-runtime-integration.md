---
guardian_issue:
  id: "ISSUE-RUNTIME-INTEGRATION"
  epic: "consensus-analysis"
  component: "Runtime Integration & Legacy Migration"
  module: "consensus-analysis"
  status: planned
  priority: high
  dependencies: []

  in_scope:
    - Wire the new service(s) into the REAL runtime path — every choke point the module doc
      documents (primary dispatch loop PLUS parallel / resume / hook variants; not just one seam)
    - Remove or delegate the legacy path the module replaces (legacy symbol deleted or calling
      the new service); honor any declared migration rule (e.g. GAP-N)
    - Flip the feature ADR from Proposed to Accepted once wired
    - Add an end-to-end test through the PUBLIC API that exercises the new path

  out_of_scope:
    - New feature behavior beyond wiring
    - Schema/data migrations (unless the module doc's migration rule requires them)

  canonical_references:
    - module: ".pi/architecture/modules/consensus-analysis.md"
    - adr: ".pi/architecture/decisions/ADR-009-runtime-wiring-multilang-judgment.md"

  acceptance_criteria:
    - "New service reachable from the runtime entry path (production, non-test caller)"
    - "Legacy path removed or delegating; migration rule honored"
    - "Feature ADR Accepted"
    - "E2E through the public API exercises the new path"
    - "validate-runtime-wiring.sh passes for the module (no dead service)"

  validators:
    - ci
    - tests
    - architecture
    - operations
    - canonical

  implementation_notes: |
    Run .pi/scripts/validate-runtime-wiring.sh before and after. If the new service
    is only referenced by its own tests, it is NOT integrated. Converting the
    documented dispatch choke point(s) is the acceptance slice — do not close this
    issue with an honest deferral note.

  file_changes:
    - "modify: runtime dispatch / composition root (per module doc integration section)"
---

# Runtime Integration & Legacy Migration: consensus-analysis

## Intent

The implementation issues above delivered tested components. This issue makes them
**actually run**: wire them into the runtime dispatch path, retire the legacy path,
and prove it with an end-to-end test — per ADR-009 (implemented-but-unwired is the
gap this closes).

> No explicit integration section found in the module doc — trace the runtime entry path (dispatch/composition root) yourself.

## Acceptance Criteria

| # | Criterion | How to Verify |
|---|-----------|---------------|
| 1 | Service reachable from runtime entry path | grep production (non-test) caller outside the module |
| 2 | Legacy path removed or delegating | legacy symbol deleted / delegates to new service |
| 3 | Feature ADR Accepted | ADR Status not Proposed |
| 4 | E2E exercises the new path through the public API | integration/e2e test |
| 5 | validate-runtime-wiring.sh passes | script exit 0 |
