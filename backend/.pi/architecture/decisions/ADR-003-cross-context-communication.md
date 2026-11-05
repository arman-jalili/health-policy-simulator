# ADR-003: Cross-Context Communication

**Status:** Accepted
**Date:** 2026-11-05
**Session:** 87433e56-b1a2-4464-a232-2dc4fe6f9dfd

## Context

Ten contexts must cooperate without becoming one tangled module. Two integration styles were
considered: synchronous port calls and asynchronous domain events. The simulator needs both —
retrieval must answer *now* (the agent is waiting), while consensus and briefing are derived
after a run closes.

A specific risk: **LangGraph orchestration state must not become the source of truth.** If the
workflow graph holds negotiation state, then pausing, resuming, replaying or auditing depends on
graph internals, and the domain model becomes decorative.

## Decision

**Two channels, with a strict ownership rule.**

1. **Synchronous, in-process ports** for request/response needs:
   - `EvidenceRetrieval` consumes `EvidenceCorpus`'s published language
     (`PassageView`, `ProvenanceView`) through a defined port — never through its tables.
   - `NegotiationSession` consumes `EvidenceRetrieval`'s `EvidencePack` through an
     anti-corruption layer that maps it to `ClaimEvidence` refs. Raw vector hits never reach
     the negotiation domain.
   - `NegotiationSession` consumes `StakeholderModel`'s `StakeholderProfileView` (partnership).

2. **Asynchronous domain events** through a transactional outbox for everything else:
   `NegotiationSession → ConsensusAnalysis` (open-host, session events are the published contract),
   `ConsensusAnalysis → DecisionBrief` (conformist, brief projects consensus records),
   `ClaimValidation → NegotiationSession` (partnership, verdicts gate arguments).

**Ownership rule:** the domain owns state; LangGraph owns *sequencing*. Every graph node calls an
application service command and then re-reads state from a repository. No node mutates domain
state directly, and graph state carries only ids and phase markers.

**Event contract rules**
- Events are named in the past tense and are immutable facts.
- Payloads carry ids plus the minimum data a consumer needs; consumers re-read for detail.
- Every event is persisted (outbox + append-only log) so runs can be replayed.
- A consumer that fails retries idempotently: every handler keys on `event_id`.

## Consequences

- Pause/resume and crash recovery are state-loading problems, not graph-serialisation problems.
- Context coupling is explicit and listable — see the event-flow diagram.
- Eventual consistency appears in the brief: it must state the round it projects to.
- Debugging requires reading the event log; a `/runs/{id}/events` endpoint makes this routine.

## Alternatives Considered

| Alternative | Why rejected |
|---|---|
| All-synchronous ports | Consensus/brief would block the run; long chains of in-process calls hide coupling |
| All-events | Retrieval latency becomes unacceptable inside an agent turn |
| Shared graph state as truth | Violates auditability; resume/rewind depends on framework internals |
| Message broker (Kafka/NATS) | Operational cost without benefit at prototype scale; outbox keeps the seam |

## Affected Modules

EvidenceCorpus, EvidenceRetrieval, StakeholderModel, NegotiationSession, ConsensusAnalysis,
DecisionBrief, ClaimValidation, SimulationOrchestration, GovernanceCompliance
