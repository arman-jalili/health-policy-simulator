# ADR-001: Domain-Driven Design with Bounded Contexts

**Status:** Accepted
**Date:** 2026-11-05
**Session:** 87433e56-b1a2-4464-a232-2dc4fe6f9dfd
**Supersedes:** —  **Superseded by:** —

## Context

The domain exploration identified ten bounded contexts for a negotiation simulator in which
institutional agents argue over Austrian healthcare policy. The contexts differ sharply in
weight: six carry real domain rules (evidence provenance, negotiation state, consensus
derivation, claim verification, briefing, stakeholder identity), two are supporting plumbing
(workflow orchestration, output governance), one is commodity (identity/access).

The deliverable is a hackathon prototype that must still be defensible as an auditable system:
every claim in a published brief must resolve to a page in a press archive, and every position
change must carry a reason.

## Decision

Adopt **Domain-Driven Design** with bounded contexts implemented as a **modular monolith**:

- One deployable Python/FastAPI application, one PostgreSQL database.
- Each context is a package under `src/<context>/` with four layers:
  `domain/`, `application/`, `infrastructure/`, `interfaces/`.
- Layers may only depend inward. `domain/` imports nothing from the other three.
- No cross-context imports at the `domain/` layer. Contexts integrate through:
  published-language ports (EvidenceCorpus → EvidenceRetrieval) and domain events.
- Transaction boundaries are owned by application services, never by handlers or repositories.

## Consequences

**Positive**
- Domain rules are testable without HTTP, database or LLM calls.
- Contexts can be extracted into services later without rewriting domain logic.
- The evidence chain (passage → claim → argument → position → brief section) is enforceable
  by types rather than by convention.

**Negative / costs**
- More files than a single-module FastAPI app; discipline is required not to leak layers.
- Cross-context queries that would be a SQL join must become an explicit port or projection.
- The modular monolith tempts shared "utils" packages that erode boundaries — architecture
  validators must check this (see ADR-008 and `.pi/validators/architecture`).

## Alternatives Considered

| Alternative | Why rejected |
|---|---|
| Single-package FastAPI app | No enforcement of the evidence chain; the transparency requirement becomes a convention that decays under deadline |
| Microservices per context | Operational overhead with zero demo benefit; ten services for one prototype |
| Layered architecture (controllers/services/repositories) | Organises by technical role, not by domain; the negotiation state machine would be smeared across layers |
| Agent-first design (LangGraph as the model) | Rejected explicitly in ADR-003: graph state is not the source of truth |

## Affected Modules

EvidenceCorpus · EvidenceRetrieval · StakeholderModel · NegotiationSession · ConsensusAnalysis ·
DecisionBrief · ClaimValidation · SimulationOrchestration · GovernanceCompliance · IdentityAccess
