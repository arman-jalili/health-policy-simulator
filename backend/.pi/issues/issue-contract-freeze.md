---
guardian_issue:
  id: "ISSUE-CONTRACT-FREEZE"
  epic: "governance-compliance"
  component: "Contract Freeze"
  module: "governance-compliance"
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
    - module: ".pi/architecture/modules/governance-compliance.md"

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
    - "create: src/governance-compliance/domain/"
    - "create: src/governance-compliance/application/"
    - "create: src/governance-compliance/infrastructure/"
    - "create: src/governance-compliance/interfaces/"
---

# Contract Freeze: governance-compliance

## Intent

Define and freeze all public interfaces, contracts, and schemas for the governance-compliance
epic before any implementation begins. This prevents architecture drift — implementation
must satisfy contracts, not the other way around.

## Included Components

- `GC-001`
- `GC-002`
- `GC-003`
- `GC-004`
- Determinism
- Violation persistence
- Provenance completeness
- Adversarial suite
- Port contract
- No domain model
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

## Full Implementation Sequence (for reference)

- 1. Allowlist table + loader from StakeholderModel personas
- 2. `GC-001` rule + tests with a corpus of adversarial strings
- 3. `GC-002` quotation rule using `speaker_kind`
- 4. Rewrite path + `ViolationRecord` persistence
- 5. `EnforceInstitutionOnlyOutput` port for NegotiationSession (contract test)
- 6. `DisclosePositionProvenance` assembler
- 7. REST endpoints + read models
- 8. Adversarial regression suite (≥30 cases) run in CI



## Implementation

> **Agent:** Create interface-only files. No implementation. Use Clean Architecture layers:
> 1. Read the architecture module to understand each component's role
> 2. Place domain interfaces in domain/, service interfaces in application/, DTOs in application/
> 3. Controllers/routers are CONCRETE — they do NOT get interfaces. The concrete router/handler class goes directly in interfaces/http/ without a separate contract file.
> 4. Event schemas go in domain/event/
> 5. Repository interfaces go in infrastructure/repository/
>
> The goal is a reviewed, frozen contract that implementation issues can depend on.
