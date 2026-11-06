# ADR-015: NegotiationSession runtime integration

**Status:** Accepted
**Date:** 2026-11-06
**Context:** negotiation-session epic (issues #281–#302)

## Decision

Wire `NegotiationSession` into the modular monolith as the domain core the orchestrator drives:

- `shared/app.py` builds one container through `negotiation_session.composition.build_container`
  and mounts `negotiation_session_router`; the container is exposed on
  `app.state.negotiation_session`.
- Every ACL port is bound to a real upstream context:
  - `RetrievalEvidencePacks` → `EvidenceRetrieval.get_pack`, mapped to vector-free
    `ClaimEvidence` (`EvidencePackView` → `ClaimEvidence`).
  - `StakeholderProfiles` → `StakeholderModel.get_profile`, mapped to the domain
    `StakeholderBinding` (the domain imports no upstream layer).
  - `ClaimVerdicts` → `ClaimValidation.verify_claim`; only `verified` or explicitly
    `unsupported` claims pass the gate.
  - `GovernanceGuardAdapter` → `GovernanceCompliance.enforce_institution_only_output`. It is
    blocking on the write path and **fails closed**: an unbound guard raises
    `GOVERNANCE_GUARD_UNAVAILABLE`, it never permits.
  - `RequiredInvocationLookup` rejects an argument without its invocation id (ADR-006).
- The SSE route shares the per-run ordered broker and replays contiguously after
  `Last-Event-ID`; invalid ids are a `400 BAD_REQUEST`.
- Persistence: the container uses the in-memory aggregate/event-log adapters for both configured
  persistence families. The append-only log allocates gap-free per-run ordinals atomically (W9).
  SQLAlchemy adapters and migrations `0401`/`0402` remain a tracked follow-up; the module runbook
  documents the restart/replay expectation for them.
- No legacy negotiation path exists: the aggregate is new, so there is nothing to delete or
  delegate to.

## Consequences

- The public API can open a run, read its state, replay `/events` and stream ordered frames.
- A missing guard blocks all position/argument writes instead of silently persisting them.
- Replay folds the log to the same `SimulationRunResult` the live repository projects, so audit
  and live state cannot diverge within a round bound.
- The deferred SQLAlchemy family is the only production gap; it is visible in the runbook and
  the architecture readiness checklist rather than hidden behind a permissive default.
