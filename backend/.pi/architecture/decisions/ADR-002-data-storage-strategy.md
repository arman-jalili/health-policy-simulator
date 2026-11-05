# ADR-002: Data Storage Strategy

**Status:** Accepted
**Date:** 2026-11-05
**Session:** 87433e56-b1a2-4464-a232-2dc4fe6f9dfd

## Context

The system must persist: an ingested press corpus with page-level provenance, a negotiation
event history, agent invocations with prompt/model versions, derived analysis artefacts and
published briefs. Reproposability matters — a brief must remain explainable after re-ingestion.

**Language deviation (explicit):** the task brief for this ADR names *Postgres + SQLx*, which is
the Rust driver. `guardian-manifest.json` declares `"language": "python"` and the UC2 technology
baseline is Python/FastAPI. SQLx is therefore not applicable; the equivalent decision is
**PostgreSQL + SQLAlchemy 2.x async (asyncpg) + Alembic**. The scaffold emitted Rust stubs; those
are corrected throughout the module docs. Recorded here rather than silently swapped.

## Decision

**One PostgreSQL 16 database, schema-per-context.** No context reads another context's tables
directly; it consumes a port, a projection or an event.

| Concern | Choice | Rationale |
|---|---|---|
| ORM / data access | SQLAlchemy 2.x async + asyncpg | Mature async support, typed models, Alembic integration |
| Migrations | Alembic, one revision chain, context-prefixed tables | Single database, ordered migrations, per-context table ownership |
| Table ownership | `<context_snake>_<entity>` e.g. `negotiation_session_run` | Ownership is visible in the table name; validators can enforce it |
| Full-text search | PostgreSQL `tsvector` + GIN, German config | Avoids operating a separate BM25 service for the prototype |
| Vector search | `pgvector` HNSW index on `passage_embedding` | One datastore; Qdrant is deferred until corpus size demands it |
| Domain events | Transactional **outbox** table written in the same transaction as the state change | No lost events, no distributed transaction |
| Event relay | In-process dispatcher polling the outbox (Phase 1) | Upgradeable to a broker without touching domain code |
| LLM/agent payloads | JSONB columns with schema version | Prompt/model evolution without migrations per change |
| Corpus snapshot pinning | `corpus_snapshot` row + immutable `passage` rows | Citations remain valid after re-ingestion |

**Aggregate-per-transaction rule:** a transaction loads and saves exactly one aggregate root.
Cross-aggregate consistency is eventual, via events. This is why `Document` is per-file and
`CorpusSnapshot` is a manifest rather than one giant corpus aggregate.

**Retention:** raw source files stay on disk/object storage, referenced by content hash.
The database stores derived text only, so a re-extraction never destroys the original.

## Consequences

- One database to back up, migrate and query; no distributed transactions.
- The outbox adds a table and a relay loop, but makes replay (`ReplaySimulationHistory`) trivial.
- PostgreSQL-specific search features reduce portability; accepted for the prototype.
- Vector recall at prototype scale is adequate; the Qdrant migration path is documented in
  the EvidenceRetrieval module.

## Alternatives Considered

| Alternative | Why rejected |
|---|---|
| One schema, shared tables | Ownership becomes invisible; cross-context writes become accidental |
| MongoDB for event history | Loses relational integrity for the evidence chain, which is the point |
| Qdrant + Elasticsearch from day one | Two extra services to operate for a demo dataset |
| Event sourcing as the only store | Correct but expensive; we keep an event log *and* current-state tables |

## Affected Modules

All contexts. Tables: `evidence_corpus_*`, `evidence_retrieval_*`, `stakeholder_model_*`,
`negotiation_session_*`, `consensus_analysis_*`, `decision_brief_*`, `claim_validation_*`,
`simulation_orchestration_*`, `governance_compliance_*`, `identity_access_*`, `shared_event_outbox`.
