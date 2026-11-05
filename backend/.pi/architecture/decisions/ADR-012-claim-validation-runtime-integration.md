# ADR-012: ClaimValidation Runtime Integration

**Status:** Accepted
**Date:** 2026-11-06
**Session:** claim-validation epic (#163)

## Context

ClaimValidation was implemented component by component: values, `Claim` aggregate, type dispatch,
tolerance, contradiction detection, reference provenance, escalation, unsupported retention, number
parsing, measure identity and the HTTP surface. ADR-009 names the failure mode: a green suite with no
production caller.

The verifier must run against the same composition root as the process, persist claims and reference
figures, and refuse contradicted/unsupported claims downstream through a published view.

## Decision

**ClaimValidation is wired in `shared.app` and its only public entry path is the HTTP router.**

- `shared.app.create_app` builds `claim_validation.composition.build_container(settings, database)`
  and mounts `claim_validation_router`; the container is exposed as `app.state.claim_validation`.
- `PERSISTENCE=postgres` wires `SqlAlchemyClaimRepository`,
  `SqlAlchemyReferenceFigureRepository` and `SqlAlchemyContradictionRepository`; memory remains the
  explicit local/test family.
- Migration `0301_claim_validation` creates `claim_validation_claim`,
  `claim_validation_reference_figure` and `claim_validation_contradiction`. Aggregate payloads are
  JSONB; measure keys are duplicated for equality lookups.
- The reference-figure table is deliberately **not** seeded with invented values. An empty table
  makes a quantitative claim `AMBIGUOUS`, never `VERIFIED`; authoritative figures are registered via
  `POST /api/v1/reference-figures`.
- The router's seven routes delegate to application services. `ClaimVerdictView` is the published
  boundary: no vectors, ORM models or repository objects leave the context.
- Pre-wiring bodies raising `NotImplementedError` are gone; no legacy verification path remains.

## Alternatives Considered

| Alternative | Pros | Cons | Reason Rejected |
|---|---|---|---|
| Leave the module as a test-only library | No wiring work | Violates ADR-009; no public proof | The verifier must run |
| Seed invented `ReferenceFigure` rows | Demo looks populated | Fabricated authoritative figures | Misinformation is worse than `AMBIGUOUS` |
| Store only in memory | Simple | Verdict history and reference figures vanish | Audit requirement |
| Expose ORM/JSONB directly | Less mapping | Leaks persistence into consumers | Violates ACL boundary |

## Consequences

### Positive

- The same composition root and router are exercised by production and integration tests.
- Empty reference data is honest: the API reports `AMBIGUOUS`.
- Claims, reference figures and contradictions survive a restart.
- Downstream receives only `ClaimVerdictView`.

### Negative

- Operators must register reference figures before quantitative claims can verify.
- JSONB payloads keep the aggregate shape but limit SQL queries to measure keys today.

### Neutral

- Causal appraisal is deterministic until the metered LLM adapter lands; it never yields `VERIFIED`.
- Legal evidence currently yields `UNSUPPORTED` unless a provision source is supplied.

## Implementation

**Affected Modules:**
- `.pi/architecture/modules/claim-validation.md`

**Files to Update:**
- `src/shared/app.py`
- `src/claim_validation/composition.py`
- `src/claim_validation/infrastructure/repository/sqlalchemy.py`
- `migrations/versions/0301_claim_validation.py`
- `tests/integration/test_claim_validation_wiring.py`
- `tests/integration/test_claim_validation_persistence.py`

**Canonical References:**
Implementation files reference `.pi/architecture/decisions/ADR-012-claim-validation-runtime-integration.md`.
