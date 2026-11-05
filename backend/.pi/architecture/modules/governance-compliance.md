# GovernanceCompliance

## Module Status

**Status:** Implemented
**Depends:** StakeholderModel (institutional allowlist), EvidenceCorpus (`speaker_kind` attribution), ClaimValidation (figure findings), SimulationOrchestration (invocation records)
**Last reviewed:** 2026-11-05
**Source session:** 87433e56-b1a2-4464-a232-2dc4fe6f9dfd

## Description

Enforces that only institutions are represented, that no real person is named or quoted, and that
every position can be explained by its sources, arguments and model invocation.

**Modeling Depth:** service (supporting subdomain)
**Subdomain Rationale:** Hard regulatory requirement from the challenge; enforcement must be explicit.
**Context Map:** anticorruption-layer → NegotiationSession (Guards agent output; rejects person-level references before persistence).

## Architecture

| Layer | Responsibility | Path |
|-------|--------------|------|
| **Domain** | — (empty ADR-008 marker; no aggregates, VOs or domain events) | `src/governance_compliance/domain/__init__.py` |
| **Application** | `EnforceInstitutionOnlyOutput`, `DisclosePositionProvenance`, `RecordGovernanceViolation` | `src/governance_compliance/application/` |
| **Infrastructure** | NER adapter, rule engine, violation repository, provenance assembler | `src/governance_compliance/infrastructure/` |
| **Interfaces** | Guard port consumed by NegotiationSession; REST read endpoints | `src/governance_compliance/interfaces/` |

**Anti-corruption edge:** `GovernanceCompliance → NegotiationSession`. The guard is invoked *before*
any argument or position is persisted. It returns a verdict, never a mutated domain object.

## Contract Freeze (issue #248)

The frozen surface is documented in [`docs/contracts-governance-compliance.md`](../../../docs/contracts-governance-compliance.md):
application values, commands, DTOs, services, rules, ports, repository ports, error codes, five HTTP
routes and the published guard/provenance views. The guard rule chain lives in `application/rules.py`,
not `domain/`, because ADR-008 forbids domain modules for this service-depth context.

The freeze is additive-only. Renaming or removing a frozen member requires a new contract-freeze
issue; implementation issues may fill bodies but must not change signatures.

## Related ADRs

| ADR | Relevance |
|---|---|
| ADR-007 Compliance Engine Architecture | Primary design: two-stage guard, deterministic checks, persisted violations |
| ADR-003 Cross-Context Communication | Guard sits in front of the negotiation write path |
| ADR-006 Cost Tracking | Rejected/rewritten outputs are still metered |
| ADR-008 Proportional Modeling Depth | Service depth: no aggregates, no domain events of its own |
| ADR-014 GovernanceCompliance Runtime Integration | Guard/router/container mounted; empty allowlist aborts boot; no LLM on the guard path |

## Diagrams

### Data Flow

```mermaid
flowchart LR
    A[Agent output<br/>argument / position / proposal] --> B[Guard: person reference]
    B --> C[Guard: direct quotation]
    C --> D[Guard: unsupported figure]
    D --> E{Verdict}
    E -->|accept| F[Return to NegotiationSession]
    E -->|rewrite| G[Record rewritten span] --> F
    E -->|reject| H[RecordViolation] --> I[Reject to caller]
    F --> J[Persist argument]
    J --> K[DisclosePositionProvenance]
    K --> L[Provenance record for brief]
```

### Entity Relationship

```mermaid
classDiagram
    class GuardVerdict {
        +str decision
        +list violations
        +str rewritten_text
    }
    class ViolationRecord {
        +str violation_class
        +str offending_span
        +str rewritten_span
        +str invocation_id
    }
    class ProvenanceRecord {
        +str position_id
        +list evidence_ids
        +list argument_ids
        +str invocation_id
        +str prompt_version
    }
    class InstitutionalAllowlist {
        +list canonical_names
        +list aliases
    }
    GuardVerdict "1" --> "*" ViolationRecord
    ProvenanceRecord "1" --> "1" InstitutionalAllowlist : validated against
```

### Data Flow (provenance disclosure)

```mermaid
sequenceDiagram
    participant App as DisclosePositionProvenance
    participant SN as NegotiationSession
    participant CV as ClaimValidation
    participant SO as SimulationOrchestration
    participant DB as ProvenanceStore
    App->>SN: position + cited evidence ids
    App->>SN: revision argument ids
    App->>SO: invocation id + prompt version
    App->>CV: claim verdicts for the position
    App->>DB: save ProvenanceRecord
    DB-->>App: disclosed
```

### Key Use Case Sequence — EnforceInstitutionOnlyOutput

```mermaid
sequenceDiagram
    participant NS as NegotiationSession
    participant Guard as EnforceInstitutionOnlyOutput
    participant Allow as Allowlist + NER
    NS->>Guard: check(text, speaker_kind, invocation_id)
    Guard->>Allow: scan person references
    Allow-->>Guard: hits[]
    alt person named
        Guard->>Guard: attempt rewrite (drop span, keep institution sentence)
        Guard-->>NS: rewrite{text, violation}
    else personal quotation
        Guard-->>NS: reject{violation}
    else clean
        Guard-->>NS: accept
    end
    Guard->>Guard: RecordGovernanceViolation if not clean
```

## Service + Persistence Contract

| Operation | Reads | Writes | Idempotent |
|---|---|---|---|
| `EnforceInstitutionOnlyOutput` | allowlist, NER model, `speaker_kind` map | `governance_compliance_violation` | yes (keyed by `invocation_id` + span hash) |
| `DisclosePositionProvenance` | positions, arguments, invocations, verdicts | `governance_compliance_provenance` | yes (keyed by `position_id`) |
| `RecordGovernanceViolation` | — | `governance_compliance_violation` | yes (unique on `violation_hash`) |

**Persistence contract**

| Table | Columns (essential) | Ownership note |
|---|---|---|
| `governance_compliance_violation` | `id, violation_class, offending_span, rewritten_span, invocation_id, detected_at, rule_id` | Append-only; never updated |
| `governance_compliance_provenance` | `position_id, evidence_ids[], argument_ids[], invocation_id, prompt_version, model, disclosed_at` | Append-only; one per position per version |
| `governance_compliance_allowlist` | `canonical_name, kind, aliases[]` | Operator-curated, versioned |

## Components

**Service depth (ADR-008): no aggregates, no value objects, no domain events.** The module is
defined by its application services and its persistence contract above.

| Component | Layer | Responsibility |
|---|---|---|
| ``EnforceInstitutionOnlyOutput` / `DisclosePositionProvenance` / `RecordGovernanceViolation`` | application | Guard and provenance orchestration (catalog above) |
| `GuardRuleChain` (`GC-001`…`GC-005`) | application (rules) | Deterministic rule evaluation returning accept / rewrite / reject |
| `ViolationStore`, `ProvenanceStore`, `AllowlistLoader` | infrastructure | Append-only persistence; keyed for idempotency |
| `require_scope` guarded routers | interfaces | Guard, violations, provenance, allowlist endpoints |

## Application Services (authoritative catalog)

| Service | Use case | Maps to FR |
|---|---|---|
| `EnforceInstitutionOnlyOutput` | Reject agent output that names or quotes real persons before it reaches persistence. | FR-025 |
| `DisclosePositionProvenance` | Produce the derivation record for each position: sources, arguments and model invocation reference. | FR-026 |
| `RecordGovernanceViolation` | Persist a rejected agent output with its violation class, the offending span and the rewrite that replaced it, so the transparency rule is provably enforced. | FR-025 |

**Additional helper (below the catalog, not a replacement):** `ValidateInstitutionalAllowlist` —
operator tool to check that all nine personas resolve to allowlist entries.

## Guard rules (service behaviour)

| Rule id | Check | Implementation | Verdict on hit |
|---|---|---|---|
| `GC-001` | Named person in agent output | **honourific regex only** (`Dr.`, `Mag.`, `Prof.`, `Dipl.-Ing.`, `Obmann`, `Obfrau`, `Präsident(in)`) — no NER model, no allowlist consultation | rewrite (span → `[person]`) |
| `GC-002` | Direct quotation attributed to a person | `speaker_kind` **supplied by the caller** (not read from the passage) + the first quoted span anywhere in the text (no sentence window) | reject |
| `GC-003` | Institution referenced by a person's name | only the literal phrase `minister('s)? ministry` / `ministerium des ministers`, resolved against the allowlist aliases | rewrite to canonical name |
| `GC-004` | Claim without citation presented as fact | absence of **caller-supplied** `cited_passage_ids` / `reference_figure_ids` (the ids are not derived from the text) | rewrite to `unsupported:` prefix |
| `GC-005` | Figure contradicted by `ReferenceFigure` | **not wired**: the container binds a lookup that returns `None` for every id, so the rule never fires | (intended) reject |

**Deterministic by design.** Rule evaluation is a fixed sequence of regex/string rules and a table
lookup. No LLM decides compliance (ADR-007), and provider adapters cannot be imported from
`application/` (AST-enforced). Every verdict is reproducible for the same input.

### Guard fidelity — what these rules actually catch

The five rules are **heuristics with declared inputs**, not a classifier. They are honest about that only
if this table is read with them:

| Rule | Catches | Misses (observed) | Tracked |
|---|---|---|---|
| GC-001 | `Dr. Kurz`, `Prof. Dr. Meier` | `Sebastian Kurz`, `Kurz`, `DR. KURZ`, `Kurz'` | #266 |
| GC-002 | a quotation when the body declares `speaker_kind: person` | the same quotation labelled `institution` | #267 |
| GC-003 | `minister's ministry`, `Ministerium des Ministers` | `Kurz' Ministerium`, possessive forms | #266 |
| GC-004 | uncited sentences that smell like facts (`ist/sind/beträgt/…` or a number) | a bare assertion with no copula and no number | — |
| GC-005 | nothing today — the verdict lookup is a stub that returns `None` | every contradicted figure | #265 |

Chain semantics: the chain stops at the first non-`ACCEPT` rule, so a `REWRITE` suppresses a later
`REJECT` and only one violation per call is persisted (#268). Do not present the guard as
"rejects contradicted figures" until #265 is closed.

## API Endpoints

| Method | Path | Handler | Input | Output | Auth |
|---|---|---|---|---|---|
| POST | `/api/v1/governance/check` | `enforce_institution_only_output` | `{text, speaker_kind, invocation_id}` | `{decision, violations[], rewritten_text?}` | `runs:write` |
| GET | `/api/v1/governance/violations` | `list_violations` | `?run_id&class` | violation records | `runs:read` |
| GET | `/api/v1/positions/{position_id}/provenance` | `get_position_provenance` | — | evidence + arguments + invocation + prompt version | `runs:read` |
| POST | `/api/v1/positions/{position_id}/provenance` | `disclose_position_provenance` | `{}` | `201 provenance record` | `runs:write` |
| GET | `/api/v1/governance/allowlist` | `list_allowlist` | — | institutions + aliases | `admin` |

## Ubiquitous Language

| Term | Definition |
|---|---|
| Institutional Representation | The rule that agents represent institutions, never natural persons |
| Guard Verdict | accept / rewrite / reject for one agent output |
| Violation Class | `person_named`, `personal_quotation`, `unsupported_fact`, `contradicted_figure` |
| Offending Span | Exact text fragment that triggered the guard |
| Rewritten Span | Replacement text when the verdict is rewrite |
| Institutional Allowlist | Curated set of legitimate institution names and aliases |
| Provenance Disclosure | Evidence + arguments + invocation behind one position |

## Dependencies

**Depends On:**

| Module | What it provides |
|---|---|
| StakeholderModel | Canonical institutional names and aliases — the allowlist source of truth |
| EvidenceCorpus | `speaker_kind` per passage, so personal quotations are identifiable |
| ClaimValidation | Figure verdicts for `GC-005` |
| SimulationOrchestration | `invocation_id`, model and prompt version for disclosure |

**Used By:**

| Consumer | What it provides |
|---|---|
| NegotiationSession | Pre-persistence guard + provenance disclosure gate |
| DecisionBrief | Disclosure presence required before publication |

## Implementation Sequence

1. Allowlist table + loader from StakeholderModel personas
2. `GC-001` rule + tests with a corpus of adversarial strings
3. `GC-002` quotation rule using `speaker_kind`
4. Rewrite path + `ViolationRecord` persistence
5. `EnforceInstitutionOnlyOutput` port for NegotiationSession (contract test)
6. `DisclosePositionProvenance` assembler
7. REST endpoints + read models
8. Adversarial regression suite (≥30 cases) run in CI

## Patterns & OOP Mapping

| Component | Pattern | Rationale |
|---|---|---|
| Guard rules | **Chain of Responsibility** | `GC-001 → GC-002 → …`; each rule may accept, rewrite or reject |
| Allowlist matching | **Specification** | `IsInstitutionName`, `HasPersonTitle`, `IsPersonAlias` combine cleanly |
| Guard output | **Result object** (`GuardVerdict`) | Explicit accept/rewrite/reject instead of exceptions as control flow |
| Provenance assembly | **Assembler / DTO** | Combines four sources into one immutable disclosure record |
| No aggregates | — | ADR-008 service depth: persistence contract instead of domain model |

**Explicitly rejected:** LLM-as-judge for compliance. It cannot be unit-tested, cannot be replayed
and can be argued with — three disqualifying properties for a compliance control.

## Wiring Contract

| Wiring point | Requirement | Proof |
|---|---|---|
| Router | `app.include_router(governance_compliance_router)` | boot test asserting registration |
| Composition | allowlist loaded from StakeholderModel at startup (fail fast if empty or containing a personal name); violation and provenance stores bound to their tables | startup test: empty allowlist aborts boot |
| Guard on the write path | `EnforceInstitutionOnlyOutput` is a **blocking** dependency of the negotiation write path; a missing guard must fail closed | negative test: guard unbound ⇒ argument write returns 5xx, never persists |
| Persistence | Migration `0305` applied; violations append-only and idempotent on `violation_hash` | restart + duplicate-retry test |
| Determinism | No LLM call in the guard path; rule version recorded per violation | unit test monkeypatching the LLM client to raise — guard must still work |
| Provenance | **Deferred.** `DisclosePositionProvenance` reads from a stub (`_NoFacts`) that always returns an incomplete record, so the endpoint answers 422 for every request; the complete source (SimulationOrchestration invocations + ClaimValidation verdicts) is not wired | #269 — the rejection is correct, the source is missing; `/readyz` must report the degraded posture |


### Collaborator reachability (W8)

Every row is a call-site obligation, not a description: the collaborator must be invoked from the named entry point, and its effect must be visible from outside the module. A collaborator with no row here is a defect in this document. A unit test of the collaborator is never proof of wiring — the proof drives the entry point and reads the effect. Enforced mechanically by
`.pi/scripts/ci/check_collaborator_reachability.py`, which fails CI when a collaborator is assigned in
`__init__` and never read.

| Collaborator | Invoked from | Observable effect | Fails when |
|---|---|---|---|
| institution allowlist | boot | boot aborts on an empty or personal-name allowlist | an empty allowlist is treated as "permit all" |
| rule engine | every argument write | `rule_version` recorded on each violation row | a violation is recorded without a rule version |
| `violation_hash` uniqueness | retry path | a duplicate retry yields one row | duplicate rows on retry |
| `DisclosePositionProvenance` | brief publication | a complete disclosure record for a real run | **current: `_NoFacts` ⇒ every request 422** (#269) |
| `ContradictedFigureRule` verdict lookup | guard, on every check with `reference_figure_ids` | `reject` on a contradicted figure | **current: `UnknownFigureVerdicts` returns `None` ⇒ rule never fires** (#265) |
| LLM independence | guard path | the guard still works with the LLM client raising | the guard calls the model and degrades to permissive |

## Acceptance Criteria

| # | Component | Criterion | Verify In |
|---|---|---|---|
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

## Modeling Depth Note (ADR-008)

This bounded context is a **supporting subdomain** — modelled at service/CRUD depth. Keep
implementation to application services + persistence. Do NOT introduce new aggregates, value
objects, or domain events beyond what this exploration captured.

**Anti-corruption edges:**
- GovernanceCompliance → NegotiationSession — guards agent output; rejects person-level references
  before persistence, and never returns a mutated domain object.
