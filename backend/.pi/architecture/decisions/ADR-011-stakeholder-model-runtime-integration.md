# ADR-011: StakeholderModel Runtime Integration

**Status:** Accepted
**Date:** 2026-11-06
**Session:** 87433e56-b1a2-4464-a232-2dc4fe6f9dfd

## Context

StakeholderModel was implemented component by component: values, aggregates, attribution, power
derivation, veto class rule, persona cards, selection, partner contract and proofing. ADR-009 names
the failure mode this creates: a green suite with no production caller.

The context must be the source of truth for institutional identity: the running process must load
the validated persona cards, publish the institutions-only allowlist to GovernanceCompliance, and
expose the registry/selection/binding path through the public API.

## Decision

**StakeholderModel is wired in the application composition root and its only public entry path is
the HTTP router.**

- `shared.app.create_app` builds `stakeholder_model.composition.build_container(settings, database)`
  and mounts `stakeholder_model_router`.
- The composition root loads all nine YAML persona cards through `PersonaFactory`. Any invalid card
  (personal name, missing interest/constraint, unknown category/class, duplicate code) raises during
  container construction, aborting boot before the process serves.
- The validated identities are published through `PublishInstitutionalAllowlist` to
  `InstitutionalAllowlistGuard`, the source of truth that the GovernanceCompliance guard consumes.
- The eight frozen HTTP routes delegate to application services through typed mappers; the container
  is exposed as `app.state.stakeholder_model`.
- No legacy stakeholder path existed. The pre-wiring bodies raised `NotImplementedError`; they are
  replaced by real services and the router.

## Alternatives Considered

| Alternative | Pros | Cons | Reason Rejected |
|---|---|---|---|
| Leave the module as a test-only library | No wiring work | Violates ADR-009; no public proof | The module must run |
| Read persona YAML inside the router | Small wiring surface | Validation would run per request and boot could serve invalid cards | Fail-fast is the requirement |
| Keep the allowlist in GovernanceCompliance | Single guard location | Duplicates the institutional source of truth | ADR-007 makes StakeholderModel the origin |

## Consequences

### Positive

- A request exercises the same composition root and router the process uses.
- An invalid persona cannot reach the registry: boot fails first.
- GovernanceCompliance receives one published allowlist rather than reconstructing names.
- The institutional identity invariant is enforced at the aggregate and at boot.

### Negative

- Persona YAML is now a deployment input; operators must ship `backend/config/personas/`.
- The current runtime uses the in-memory repository family seeded from those cards; durable
  PostgreSQL persistence is a follow-up deployment concern, not a hidden default.
- **Deviation from ADR-002 (explicit):** this context creates no tables and owns no migration yet,
  so the schema-per-context rule in ADR-002 is not satisfied here. Recorded as D-001 in
  `.pi/architecture/DEFERRED.md`.
- **Exit criterion (when the deviation must end):** before any run in which a
  `HistoricalPosition` registered through the API influences a negotiation outcome — i.e. the
  first time NegotiationSession cites institutional history as evidence.

### Neutral

- Selection policy (weighted interest overlap) is code data, not configuration.

## Implementation

**Affected Modules:**
- `.pi/architecture/modules/stakeholder-model.md`

**Files to Update:**
- `src/shared/app.py`
- `src/stakeholder_model/composition.py`
- `src/stakeholder_model/infrastructure/personas.py`
- `src/stakeholder_model/infrastructure/guard.py`
- `src/stakeholder_model/interfaces/http/router.py`
- `tests/integration/test_stakeholder_wiring.py`

**Canonical References:**
Implementation files reference `.pi/architecture/decisions/ADR-011-stakeholder-model-runtime-integration.md`.
