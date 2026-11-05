# GovernanceCompliance frozen contract

Canonical module: `.pi/architecture/modules/governance-compliance.md`
Freeze issue: #248. Additive changes only; renaming or removing a member requires a new freeze.

## Layers (ADR-008 service depth)

| Layer | Path | Contract | Implementation |
|---|---|---|---|
| Domain | `src/governance_compliance/domain/` | Empty marker only | None — aggregates and VOs are forbidden |
| Application | `src/governance_compliance/application/` | Values, commands, DTOs, ports, repositories, rules, services, errors, events | Later component issues |
| Infrastructure | `src/governance_compliance/infrastructure/` | Repository ports; adapters added later | Later component issues |
| Interfaces | `src/governance_compliance/interfaces/` | Concrete router, HTTP schemas, published views | Later component issues |

## Values and rules

| Contract | Members |
|---|---|
| `GuardDecision` | `accept`, `rewrite`, `reject` |
| `ViolationClass` | `person_named`, `personal_quotation`, `institution_ambiguous`, `unsupported_fact`, `contradicted_figure` |
| `SpeakerKind` | `institution`, `person`, `anonymous` |
| `FigureVerdict` | `verified`, `contradicted`, `unsupported`, `ambiguous`, `missing` |
| `GuardRuleId` | `GC-001`, `GC-002`, `GC-003`, `GC-004`, `GC-005` |
| `InstitutionalAllowlist` | `institutions`, `version`; `is_empty`, `canonical_names`, `aliases` |
| `AllowlistEntry` | `code`, `canonical_name`, `short_name`, `category`, `aliases` |

`GuardRuleChain(rules)` evaluates `GuardRuleContext` in fixed order. The first non-accept result wins.
The chain is deterministic: no LLM client is part of the context.

## Commands (application input)

| Command | Fields |
|---|---|
| `EnforceInstitutionOnlyOutputRequest` | `text`, `speaker_kind`, `invocation_id`, `run_id`, `position_id`, `cited_passage_ids`, `reference_figure_ids` |
| `DisclosePositionProvenanceRequest` | `position_id`, `version`, `requested_by` |
| `RecordGovernanceViolationRequest` | `run_id`, `invocation_id`, `violation_class`, `offending_span`, `rewritten_span`, `rule_id` |
| `ListViolationsRequest` | `run_id`, `violation_class`, `limit` |
| `GetPositionProvenanceRequest` | `position_id`, `version` |
| `ValidateInstitutionalAllowlistRequest` | `allowlist` |
| `ListAllowlistRequest` | no fields |

## DTOs (application output and persistence)

| Record | Fields |
|---|---|
| `ViolationRecord` | `violation_id`, `run_id`, `invocation_id`, `violation_class`, `offending_span`, `rewritten_span`, `rule_id`, `rule_version`, `violation_hash`, `detected_at` |
| `GuardVerdictResult` | `decision`, `violations`, `rewritten_text`, `rule_version` |
| `ProvenanceFacts` | `position_id`, `evidence_ids`, `argument_ids`, `invocation_id`, `prompt_version`, `model` |
| `ProvenanceRecord` | `position_id`, `evidence_ids`, `argument_ids`, `invocation_id`, `prompt_version`, `model`, `disclosed_at`, `version` |
| `ProvenanceResult` | `record` |
| `ViolationListResult` | `items` |
| `AllowlistResult` | `institutions`, `version` |
| `AllowlistValidationResult` | `valid`, `institution_count`, `problems` |

`violation_hash` is the idempotency key. `ViolationRecord` is append-only. `ProvenanceRecord` is
append-only and unique on `(position_id, version)`.

## Application services

| Service | Constructor | Execute |
|---|---|---|
| `EnforceInstitutionOnlyOutput` | `rules`, `allowlist`, `violations`, `clock`, `uow` | `async execute(EnforceInstitutionOnlyOutputRequest) -> GuardVerdictResult` |
| `DisclosePositionProvenance` | `facts`, `store`, `clock`, `uow` | `async execute(DisclosePositionProvenanceRequest) -> ProvenanceResult` |
| `RecordGovernanceViolation` | `violations`, `clock`, `uow` | `async execute(RecordGovernanceViolationRequest) -> ViolationRecord` |
| `ValidateInstitutionalAllowlist` | none | `execute(ValidateInstitutionalAllowlistRequest) -> AllowlistValidationResult` |
| `ListViolations` | `violations` | `async execute(ListViolationsRequest) -> ViolationListResult` |
| `GetPositionProvenance` | `store` | `async execute(GetPositionProvenanceRequest) -> ProvenanceResult` |
| `ListAllowlist` | `allowlist` | `async execute(ListAllowlistRequest) -> AllowlistResult` |

## Ports and repositories

| Port | Methods |
|---|---|
| `Clock` | `now()` |
| `UnitOfWork` | `transaction()` |
| `PersonNameDetector` | `detect(text)` |
| `InstitutionResolver` | `resolve(mention, allowlist)` |
| `FigureVerdictLookup` | `async verdict_for(reference_figure_id)` |
| `AllowlistSource` | `async load()` |
| `ProvenanceFactsSource` | `async load(position_id)` |
| `InstitutionGuard` | `async execute(request)` — blocking NegotiationSession port |
| `EventPublisher` | `async publish(events)` |
| `ViolationStore` | `async add`, `async get_by_hash`, `async list` |
| `ProvenanceStore` | `async save`, `async get`, `async list_for_position` |

## Error codes

| Error | Code | HTTP |
|---|---|---|
| `GovernanceViolationNotFound` | `GOVERNANCE_VIOLATION_NOT_FOUND` | 404 |
| `ProvenanceIncomplete` | `PROVENANCE_INCOMPLETE` | 422 |
| `AllowlistEmpty` | `ALLOWLIST_EMPTY` | 500 |
| `AllowlistContainsPerson` | `ALLOWLIST_CONTAINS_PERSON` | 500 |
| `GuardVerdictRequired` | `GUARD_VERDICT_REQUIRED` | 409 |
| `GuardUnavailable` | `GOVERNANCE_GUARD_UNAVAILABLE` | 503 |
| `UnknownGovernanceRule` | `UNKNOWN_GOVERNANCE_RULE` | 422 |

## HTTP routes

| Method | Path | Handler | Scope | Status |
|---|---|---|---|---|
| POST | `/api/v1/governance/check` | `enforce_institution_only_output` | `runs:write` | 200 |
| GET | `/api/v1/governance/violations` | `list_violations` | `runs:read` | 200 |
| GET | `/api/v1/positions/{position_id}/provenance` | `get_position_provenance` | `runs:read` | 200 |
| POST | `/api/v1/positions/{position_id}/provenance` | `disclose_position_provenance` | `runs:write` | 201 |
| GET | `/api/v1/governance/allowlist` | `list_allowlist` | `admin` | 200 |

Request/response field names and types are frozen in `interfaces/http/schemas.py`.

## Published language

| View | Fields | Consumer |
|---|---|---|
| `GuardVerdictView` | `decision`, `violations`, `rewritten_text`, `rule_version` | NegotiationSession |
| `PositionProvenanceView` | `position_id`, `evidence_ids`, `argument_ids`, `invocation_id`, `prompt_version`, `model`, `disclosed_at` | DecisionBrief |

## Explicit exclusions

- No `domain/` Python modules, aggregates, value objects or domain events (ADR-008).
- No database columns in this contract; the repository ports are the boundary.
- No LLM call on the guard path; determinism is part of the contract.
