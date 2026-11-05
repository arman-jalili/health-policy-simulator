# ADR-010: EvidenceRetrieval Runtime Integration

**Status:** Accepted
**Date:** 2026-11-05
**Session:** 87433e56-b1a2-4464-a232-2dc4fe6f9dfd

## Context

EvidenceRetrieval was implemented component by component: aggregate, value objects, services,
repository, hybrid search, reproducibility, ACL, evaluation and HTTP router. ADR-009 names the
failure mode this creates: a green suite with no production caller.

The context must be reachable from the process entry path, its corpus access must stay behind the
published open-host language, and a degraded embedding provider must fail readiness rather than
silently return lexical-only results labelled as hybrid.

## Decision

**EvidenceRetrieval is wired in the application composition root, and its only public entry path is
the HTTP router.**

- `shared.app.create_app` builds the EvidenceCorpus container first, then
  `evidence_retrieval.composition.build_container(settings, database, corpus=...)`, and mounts
  `evidence_retrieval_router`.
- `PassageSearchPort` is implemented by `CorpusPassageSearch`, which consumes only EvidenceCorpus'
  published ports: index writer, passage repository, snapshot repository and authority-rule
  repository. It never reads `evidence_corpus_*` tables and never imports corpus infrastructure.
- Memory mode uses the explicit in-memory pack repository; PostgreSQL mode uses the SQLAlchemy
  JSONB adapter and migration `0201_evidence_retrieval`.
- `/readyz` includes retrieval readiness. If embeddings or the reranker are unreachable the process
  returns `503 NOT_READY` with `field=evidence_retrieval`.
- No legacy retrieval path existed. The pre-wiring stubs raised `NotImplementedError`; they are
  retired in favour of the real services and the router.

## Alternatives Considered

| Alternative | Pros | Cons | Reason Rejected |
|---|---|---|---|
| Leave retrieval as a library consumed by tests only | No wiring work | Violates ADR-009; no public proof | The module must run, not just pass |
| Let retrieval import corpus repositories directly | Faster to write | Cross-context coupling; table access bypasses the open host | ADR-003 requires published language |
| Return lexical results when embeddings fail | Demo always works | Silently mislabels degraded retrieval as hybrid | Readiness must be red |

## Consequences

### Positive

- A request exercises the same composition root and router the process uses.
- Corpus access stays behind published ports; the architecture test forbids corpus infrastructure
  imports and table names.
- Operators see embedding/reranker outages in `/readyz`.

### Negative

- A SQLAlchemy pack adapter and migration are now part of the deployment surface.
- The rule-based stance baseline is deliberately weaker than a tuned model; evaluation measures it.

### Neutral

- The evaluation harness remains a CI/analyst tool, not an HTTP dependency.

## Implementation

**Affected Modules:**
- `.pi/architecture/modules/evidence-retrieval.md`

**Files to Update:**
- `src/shared/app.py`
- `src/evidence_retrieval/composition.py`
- `src/evidence_retrieval/infrastructure/adapters.py`
- `src/evidence_retrieval/infrastructure/repository/sqlalchemy.py`
- `migrations/versions/0201_evidence_retrieval.py`
- `tests/integration/test_evidence_retrieval_e2e.py`

**Canonical References:**
Implementation files reference `.pi/architecture/decisions/ADR-010-evidence-retrieval-runtime-integration.md`.
