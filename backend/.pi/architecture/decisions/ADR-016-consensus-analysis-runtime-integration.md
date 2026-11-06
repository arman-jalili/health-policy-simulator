# ADR-016: ConsensusAnalysis runtime integration

**Status:** Accepted
**Date:** 2026-11-06
**Context:** consensus-analysis epic

## Decision

Wire `ConsensusAnalysis` into the modular monolith as a derived projection over the closed run log:

- `shared/app.py` builds one container and mounts `consensus_analysis_router` alongside every other
  context. The three additions are the import block, the container assignment and the
  `include_router` call — nothing else in the app shell changes.
- The router is concrete and its seven handlers delegate to the container. Reads answer from the
  projection; before a run closes that projection is empty, which is the honest answer.
- Derivation fails closed **with a named reason** while its inputs are unpublished:
  `UnavailableRunLog`, `UnavailableMandate` and `UnavailablePowers` refuse instead of returning an
  empty agenda, a default quorum or an empty veto map. Each of those three defaults would
  manufacture agreement, which is precisely what this context exists to prevent.
- Persistence is in-memory for now (`InMemoryConsensusRepository`, `InMemoryPackageRepository`,
  `InMemoryScenarioRepository`). The PostgreSQL projection tables (`0501_consensus_analysis`, still
  reserved) land with the repository implementation; the ports already model the replace-a-run
  semantics a rebuild needs.
- Estimation registers `AssumedEstimator` only. `measured`/`derived`/`modelled` have no calculation
  and no metered client yet, so they refuse rather than guess (ADR-006).

## Consequences

- The module is reachable and observable: its routes are in the OpenAPI schema and its reads work
  end to end, proved by `tests/integration/test_consensus_e2e.py`.
- The derivation path is a call-site obligation, not a claim: it returns
  `503 CONSENSUS_ANALYSIS_UNAVAILABLE` with the missing input named until NegotiationSession
  publishes a run-log read model and a per-run mandate threshold.
- No projection table is migrated yet, so nothing can drift: the in-memory store is replaced
  wholesale by a rebuild by construction.
- Registering `container.handle_run_closed.execute` on the run-closed notice is the remaining runtime
  step, and it becomes possible the moment the run log is published.

## Alternatives considered

- **Deriving from an empty agenda until the log exists.** Rejected: an empty agenda produces
  "nothing agreed" for every topic, which reads as a result rather than as a refusal.
- **A default consensus threshold.** Rejected by the module's own W8 row: a default threshold is a
  default quorum, and `test_no_module_supplies_a_hardcoded_threshold` fails if one appears.
- **Implementing the projection tables now.** Deferred: the schema is a repository implementation
  detail, and the in-memory adapter already satisfies every port the rebuild needs.
