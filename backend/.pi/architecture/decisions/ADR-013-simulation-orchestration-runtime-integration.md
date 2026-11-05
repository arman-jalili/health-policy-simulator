# ADR-013: SimulationOrchestration Runtime Integration

**Status:** Accepted
**Date:** 2026-11-06
**Session:** simulation-orchestration epic (#204)

## Context

SimulationOrchestration was implemented component by component: graph purity/state, invocation
envelope, budget guard, pause/resume, crash recovery, SSE replay, prompt versioning, provider
independence and wiring. ADR-009 names the failure mode: a green suite with no production caller.

The worker, router and composition root must run against durable PostgreSQL when
`PERSISTENCE=postgres`, and a job started through the public API must emit progress without a manual
worker step.

## Decision

**SimulationOrchestration is wired in `shared.app`; its public entry path is the HTTP router and its
background worker runs in the application lifespan.**

- `shared.app.create_app` builds `simulation_orchestration.composition.build_container(settings,
  database)` and mounts `simulation_orchestration_router`; the container is exposed as
  `app.state.simulation_orchestration`.
- The lifespan starts `container.worker.run_forever(stop)` and stops it on shutdown. The worker
  claims queued jobs atomically (`FOR UPDATE SKIP LOCKED` on PostgreSQL).
- `PERSISTENCE=postgres` wires `SqlAlchemyJobStore`, `SqlAlchemyInvocationStore`,
  `SqlAlchemyProgressStore` and `SqlAlchemyPromptRegistry`; memory remains the explicit
  local/test family (ADR-002).
- Migration `0302_simulation_orchestration` creates `simulation_orchestration_job`,
  `_invocation`, `_progress` and `_prompt`. Invocation envelopes are unique on id; progress is unique
  on `(run_id, sequence)`; prompt versions are unique on `(name, version)`.
- The invocation envelope is append-once (`ON CONFLICT DO NOTHING`) so a retried provider call cannot
  duplicate metering.
- The unknown configured model id aborts composition at boot, never meters zero.
- `LLMClient` stays application-owned; provider adapters live only under `infrastructure/`.

## Alternatives Considered

| Alternative | Pros | Cons | Reason Rejected |
|---|---|---|---|
| Memory-only runtime | Simple | Jobs/progress vanish on restart; violates ADR-002 | Not production-safe |
| Worker as a separate process only | Clean scaling | Needs compose orchestration; no lifespan proof | Lifespan is the minimal required wiring |
| Expose ORM rows to the router | Less mapping | Leaks persistence into the API | Violates ACL boundary |
| Keep the no-op negotiation ACL forever | No Phase 4 dependency | No real turns ever run | Temporary only; replaced by NegotiationSession |

## Consequences

### Positive

- The same composition root/router/worker are exercised in production and integration tests.
- Jobs, envelopes, progress and prompts survive restart.
- `POST /runs/{id}:start` produces ordered SSE progress without manual intervention.
- Duplicate invocation ids and duplicate progress sequences fail closed.

### Negative

- Until NegotiationSession Phase 4 lands, a deterministic bootstrap node closes the run; it proves
  wiring, not negotiation depth.
- The worker is in-process; horizontal scaling requires a separate worker rollout and job locking
  already supports it.

### Neutral

- Budget guard is enforced before calls in the run-service slice; the bootstrap graph makes no LLM
  call, so a zero budget still completes.
- `SIMULATION_MODEL_ID` currently accepts the scripted adapter only; a real provider adapter is a
  future infrastructure change.

## Implementation

**Affected Modules:**
- `.pi/architecture/modules/simulation-orchestration.md`

**Files to Update:**
- `src/shared/app.py`
- `src/simulation_orchestration/composition.py`
- `src/simulation_orchestration/infrastructure/repository/{models,sqlalchemy}.py`
- `migrations/versions/0302_simulation_orchestration.py`
- `tests/integration/test_simulation_orchestration_{wiring,persistence}.py`

**Canonical References:**
Implementation files reference `.pi/architecture/decisions/ADR-013-simulation-orchestration-runtime-integration.md`.
