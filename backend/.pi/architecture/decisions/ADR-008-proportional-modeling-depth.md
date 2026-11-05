# ADR-008: Proportional Modeling Depth

**Status:** Accepted
**Date:** 2026-11-05
**Session:** 87433e56-b1a2-4464-a232-2dc4fe6f9dfd

## Context

A ten-context model expands without limit if every context is modelled tactically. Treating
`IdentityAccess` with aggregates and invariants costs the same as modelling the negotiation state
machine, while producing no differentiation. Conversely, modelling `NegotiationSession` as CRUD
would destroy the invariant that makes the result auditable ("a position cannot change without a
reason citing evidence").

The exploration classified each context as core, supporting or generic. Enrichment must follow
that classification, and validators must be able to check it mechanically.

## Decision

**Modeling depth is a property of the subdomain type, and it is enforced, not advisory.**

| Depth | Subdomain | Required modelling | Explicitly excluded |
|---|---|---|---|
| **tactical** | core | Aggregates as consistency boundaries; invariants (`rule` + what illegal state is prevented); behaviour methods (no setters on roots); domain-owned repository interfaces; value objects with entity-vs-VO justification; triaged domain events with payloads; domain/application/infrastructure service classification | — |
| **service** | supporting | Application services + persistence contract; what it reads/writes | New aggregates, value objects, domain events, wider API surface |
| **adapter** | generic | Narrow interface the domain consumes; vendor/OSS choice; ACL translation; context-map edge | Domain entities, aggregates, invariants |

**Event triage rule.** A candidate event is a domain event only if at least one holds:
a domain expert cares about it, it crosses an aggregate or context boundary, or it needs an audit
trail. Events that only describe internal processing (index writes, score computation, phase
bookkeeping) are **not** published as domain events — they may exist as logs.

**Application of the rule in this package**
- tactical: EvidenceCorpus, EvidenceRetrieval, StakeholderModel, NegotiationSession,
  ConsensusAnalysis, DecisionBrief, ClaimValidation
- service: SimulationOrchestration, GovernanceCompliance
- adapter: IdentityAccess

**Aggregate boundary rule.** An aggregate is the unit of transactional consistency, not a
structural grouping. Therefore: `Document` is per-file (not the whole corpus);
`CorpusSnapshot` is a manifest referencing documents; a `SimulationRun` does not contain the
evidence corpus.

## Consequences

- Effort concentrates where differentiation lives (evidence, negotiation, consensus).
- Supporting contexts stay small enough to finish; generic contexts are swappable.
- Over-modeled contexts are detectable by review and by the depth validator.
- Under-modeled core contexts are equally detectable — the check is bidirectional.

## Alternatives Considered

| Alternative | Why rejected |
|---|---|
| Model everything tactically | Uniform cost, no prioritisation; the prototype does not ship |
| Model everything as CRUD | Loses the auditability that is the product's premise |
| Let each context decide ad hoc | No way to review consistently; merges become arguments |

## Affected Modules

All contexts. Depth headers in each module doc are authoritative and must not be rewritten by
enrichment; `Modeling Depth Note (ADR-008)` sections record the constraint per module.
