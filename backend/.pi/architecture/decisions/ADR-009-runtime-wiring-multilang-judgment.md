# ADR-009: Runtime Wiring and Multi-Language Reachability Judgment

**Status:** Accepted
**Date:** 2026-11-05
**Session:** 87433e56-b1a2-4464-a232-2dc4fe6f9dfd

## Context

A component can pass its own tests and still be unreachable from the running process. That is the
"implemented but unwired" failure mode: a service with a green suite and no production caller. It is
invisible to unit tests and expensive to discover during an integration demo.

The Python validator originally treated the bounded context as the caller boundary, so a context's
own composition root and interface layer did not count. Every application service in a single-context
module was therefore reported as dead even when `create_app` wired it.

## Decision

**A service is runtime-reachable when production code outside its own application layer references
it.** The composition root and the interface layer are legitimate production callers; tests,
`conftest.py`, and the service's own application package do not count.

- The reachability check scans `src/**` excluding `tests/`, `test_*.py`, and
  `src/<context>/application/`.
- Every implemented module must document its runtime entry path and name the E2E proof.
- A feature ADR referenced by an implemented module must be `Accepted`, not `Proposed`.
- A legacy path must be deleted or explicitly delegate to the new runtime path.

## Alternatives Considered

| Alternative | Pros | Cons | Reason Rejected |
|---|---|---|---|
| Count only callers outside the bounded context | Catches cross-context dead code | Flags every single-context composition root as dead; noisy false positives | The composition root is the runtime entry point |
| Count any reference, including tests | Simple | A tests-only service passes | The failure mode is precisely tests-only |
| Manual review only | Flexible | Not deterministic; regresses silently | CI must enforce it |

## Consequences

### Positive

- Green tests can no longer hide an unwired service.
- The validator's rule matches the architecture: composition root + interfaces are the runtime.
- The E2E test exercises the same path the process uses.

### Negative

- A service referenced only by a future context is still reported until that caller lands.
- The heuristic is name-based; a coincidental name match can mask a dead service. The E2E test is
  the stronger proof.

### Neutral

- Multi-language support keeps the dispatcher contract: a language adapter may be absent and reports
  "not covered" rather than a false pass.

## Implementation

**Affected Modules:**
- `.pi/architecture/modules/identity-access.md`
- `.pi/architecture/modules/evidence-corpus.md`

**Files to Update:**
- `.pi/scripts/languages/python/check_runtime_reachability.sh`
- `tests/integration/test_identity_access_e2e.py`

**Canonical References:**
Implementation files should reference `.pi/architecture/decisions/ADR-009-runtime-wiring-multilang-judgment.md`.
