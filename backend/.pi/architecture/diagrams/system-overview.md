# System Architecture Overview

<!--
Canonical Reference: .pi/architecture/diagrams/system-overview.md
Status: implemented architecture (2026-11-06)
Supersedes the Guardian v1.2 blueprint placeholder.
-->

## Status and scope

This document describes the **implemented** modular monolith in `backend/`. It replaces the earlier
`api-gateway / auth-system / core / workflow / data-layer` blueprint, which never matched the code.

| Fact | Current value |
|---|---|
| Architecture pattern | DDD bounded contexts in one process ([ADR-001](../decisions/ADR-001-architecture-pattern.md)) |
| Language/runtime | Python 3.12+ (local venv currently 3.14), FastAPI, SQLAlchemy 2.x async, Alembic |
| Default persistence | PostgreSQL 16 + pgvector (`PERSISTENCE=postgres`); memory is local/test-only ([ADR-002](../decisions/ADR-002-data-storage-strategy.md)) |
| HTTP style | Versioned REST under `/api/v1`, concrete routers, additive contract freeze ([ADR-004](../decisions/ADR-004-api-design.md)) |
| Authentication | API keys + scopes in production; demo mode only on localhost ([ADR-005](../decisions/ADR-005-authentication-authorization.md)) |
| Simulation runtime | Background worker in the API process, LLM graph, durable jobs/checkpoints ([ADR-013](../decisions/ADR-013-simulation-orchestration-runtime-integration.md)) |
| Governance runtime | Guard chain before persistence, provenance disclosure ([ADR-014](../decisions/ADR-014-governance-compliance-runtime-integration.md)) |
| Frontend | Next.js App Router app in `frontend/`; talks through `/api/hps/[...path]` proxy |
| Corpus today | 231 Pressespiegel 2020 PDFs, 4,297 indexed passages, monthly snapshots |

The system is a **modular monolith**: one deployable API process, ten bounded contexts, one
database, no service mesh. Context boundaries are enforced by imports and ACL ports, not by network
hops.

---

## High-level architecture

```
┌──────────────────────────────────────────────────────────────────────────┐
│ External clients                                                         │
│   Next.js UI (frontend/)          scripts / API consumers                │
└───────────────────────────────┬──────────────────────────────────────────┘
                                │ HTTPS + X-API-Key / demo principal
                                ▼
┌──────────────────────────────────────────────────────────────────────────┐
│ shared/app.py — FastAPI application shell                                │
│                                                                          │
│   RequestContextMiddleware → auth/scope → per-context routers            │
│   /healthz  /readyz  /metrics  /api/v1/...                               │
│                                                                          │
│   ┌──────────────────────────────────────────────────────────────────┐   │
│   │ Bounded contexts (each: domain / application / infrastructure /  │   │
│   │ interfaces)                                                      │   │
│   │                                                                  │   │
│   │ IdentityAccess   StakeholderModel   EvidenceCorpus               │   │
│   │ EvidenceRetrieval ClaimValidation   SimulationOrchestration      │   │
│   │ NegotiationSession GovernanceCompliance                          │   │
│   │ ConsensusAnalysis DecisionBrief                                  │   │
│   └──────────────────────────────────────────────────────────────────┘   │
│                                                                          │
│   asyncio worker task: simulation jobs, outbox relay, recovery           │
└───────────────┬───────────────────────────────┬──────────────────────────┘
                │                               │
                ▼                               ▼
┌──────────────────────────────────┐   ┌───────────────────────────────────┐
│ PostgreSQL 16 + pgvector         │   │ External adapters                 │
│   owned tables by context prefix │   │   PyMuPDF / Tesseract (corpus)    │
│   outbox + projections + logs    │   │   LLM: scripted / OpenAI-compatible│
│   Alembic migrations 0101–0502   │   │   local PDF paths / object files  │
└──────────────────────────────────┘   └───────────────────────────────────┘
```

---

## Bounded contexts

| Context | Depth | Owns | Publishes / consumes | Persistence |
|---|---|---|---|---|
| **EvidenceCorpus** | tactical | Documents, publications, articles, passages, authority rules, snapshots, ingestion runs | Open-host: `PassageView`, provenance, index manifest | `evidence_corpus_*` |
| **EvidenceRetrieval** | tactical | Evidence packs, candidates, score breakdowns, retrieval traces | Consumes Corpus; ACL to NegotiationSession | `evidence_retrieval_*` |
| **IdentityAccess** | adapter (generic) | API keys, scopes, principal resolution | Published `Principal`; HTTP layer only | `identity_access_*` |
| **StakeholderModel** | tactical | Institutions, profiles, interests, constraints, vetoes, powers, agent bindings | Partnership ACL to NegotiationSession | `stakeholder_model_*` |
| **ClaimValidation** | tactical | Claims, verdicts, contradictions, reference figures, expert reviews | Partnership ACL to NegotiationSession / governance | `claim_validation_*` |
| **SimulationOrchestration** | service | Jobs, graph state, checkpoints, invocations, budgets, progress events, prompt registry | ACL to NegotiationSession; SSE job progress | `simulation_orchestration_*` |
| **NegotiationSession** | tactical | Mandate, run aggregate, rounds, positions, arguments, conflicts, coalitions, learning, append-only event log | Open-host to ConsensusAnalysis/DecisionBrief; ACL to orchestration | `negotiation_session_*` |
| **GovernanceCompliance** | service | Rule definitions, guard verdicts, violations, provenance disclosures | ACL guard before NegotiationSession writes | `governance_compliance_*` |
| **ConsensusAnalysis** | tactical | Derived consensus records, minorities, packages, scenarios, impact assessments | Conformist to DecisionBrief | `consensus_analysis_*` |
| **DecisionBrief** | tactical | Versioned decision briefs, cited sections, published artefacts | Consumes consensus + run history + citations + governance | `decision_brief_*` |

`src/shared/` is not a bounded context. It owns the app shell, configuration, database engine, unit of
work, outbox publisher, clocks, IDs, metrics, HTTP middleware and demo seed/walkthrough.

---

## Context map

```
                         ┌──────────────────┐
                         │  IdentityAccess  │  generic adapter
                         └────────┬─────────┘
                                  │ Principal / scopes (HTTP edge only)
                                  ▼
┌──────────────────┐     ┌──────────────────┐     ┌──────────────────┐
│  EvidenceCorpus  │────▶│ EvidenceRetrieval │────▶│ ClaimValidation  │
│  (open host)     │     │  (ACL consumer)   │     │ (partnership)    │
└────────┬─────────┘     └────────┬─────────┘     └────────┬─────────┘
         │                        │                        │
         │ PassageView            │ ClaimEvidence          │ ClaimVerdictView
         │                        ▼                        ▼
         │               ┌──────────────────────────────────────┐
         │               │        NegotiationSession            │
         │               │  run aggregate + append-only log     │
         │               └───────┬─────────────┬────────────────┘
         │                       │             │
         │ StakeholderProfileView│             │ RunClosed events
         ▼                       ▼             ▼
┌──────────────────┐    ┌──────────────────┐  ┌──────────────────┐
│ StakeholderModel │───▶│ SimulationOrch.  │  │ ConsensusAnalysis│
│ (partnership)    │    │ (service ACL)    │  │ (open-host cons.)│
└────────┬─────────┘    └──────────────────┘  └────────┬─────────┘
         │ allowlist / vetoes                          │ conformist
         ▼                                             ▼
┌──────────────────────┐                       ┌──────────────────┐
│ GovernanceCompliance │── provenance ────────▶│  DecisionBrief   │
│ (guard before write) │                       │  (versioned)     │
└──────────────────────┘                       └──────────────────┘
```

Key rules:

- **Domain layers never import another context.** Cross-context data crosses through
  `interfaces/published.py` views or application ports, mapped by ACL adapters.
- **NegotiationSession is the consistency boundary.** The graph orchestrates; it does not own run
  state. Every mutation goes through a domain command.
- **Derived artefacts are projections.** Consensus records and briefs are reproducible from the run
  log; they are persisted for read performance, not as input state.
- **Governance is on the write path.** Agent output is guarded before an argument or position is
  persisted. Provenance is produced by `CloseRound`, not by a client ceremony.

---

## Four-layer structure

Every non-adapter context follows the same inward dependency rule:

```
interfaces/  (FastAPI routers, schemas, published views, ACL adapters)
     │
     ▼
application/ (use cases, commands, DTOs, ports, rules)
     │
     ▼
domain/      (aggregates, entities, value objects, domain services, repository ports)
     ▲
     └──────── infrastructure/ implements domain/application ports
               (SQLAlchemy, PyMuPDF, Tesseract, LLM, outbox, clock)
```

| Layer | May import | Must not import |
|---|---|---|
| `domain/` | stdlib, own domain, `shared` primitives | FastAPI, SQLAlchemy, another context's internals |
| `application/` | own domain, own application ports, published ACLs | concrete infrastructure adapters |
| `infrastructure/` | own domain/application, vendor SDKs, `shared/db` | another context's infrastructure |
| `interfaces/` | own application, published views, FastAPI/Pydantic | another context's infrastructure |

ADR-008 permits **empty marker layers**: IdentityAccess has no domain/application code and
GovernanceCompliance has an empty `domain/` marker, because they are adapter/service-depth contexts.

---

## Runtime flows

### 1. Corpus ingestion

```
PDF path
  → IngestDocument (content hash, register, probe, native/OCR extraction)
  → SegmentArticle (article boundary strategy, body passage)
  → passage chunking (offline script) / :segment + :index API
  → IndexIngestedPassages (tsvector + hashing-char3gram embedding)
  → PinCorpusSnapshot (immutable document set + index manifest)
```

`scripts/ingest_corpus.py` is the offline path for large corpora: one transaction per document,
resumable by content hash, paragraph chunks, stderr progress and a JSON result on stdout.

### 2. Evidence retrieval

```
claim + claim_type + snapshot_id
  → lexical search (prefix-aware tsvector; German compound OR expansion)
  → dense search (hashing-char3gram-v1 over pinned passages)
  → reciprocal-rank fusion
  → overlap reranker + stance classification + recency weighting
  → EvidencePack (supporting + contradicting candidates, score breakdown, trace)
```

Retrieval never reads the live corpus outside the pinned snapshot. A pack records the actual index
version and embedding/reranker model ids.

### 3. Simulation run

```
POST /runs/{id}:start
  → SimulationOrchestration queues a job + budget
  → worker claims job, loads GraphState checkpoint
  → NegotiationPrepareNode (mandate / next actor)
  → NegotiationTurnNode
        → NegotiationGateway.briefing (persona + evidence + current stances)
        → LLMClient.complete (scripted or HTTP provider)
        → decision parsing / persona policy (no actor-hash fallback)
        → RecordAgentInvocation (tokens, latency, cost, model, prompt)
        → NegotiationSession command (open round, position, turn, close round)
        → GovernanceCompliance guard before persistence
  → progress events + SSE (/runs/{id}/stream)
```

The job reports `completed` only after the domain run is closed. Provider failure or unusable output
fails the job (`LLM_PROVIDER_FAILED`, `LLM_OUTPUT_UNPARSEABLE`); it never silently substitutes a
stance.

### 4. Close → consensus → brief

```
CloseRound
  → save run aggregate + append-only log
  → produce PositionProvenanceDisclosure for every open position
  → publish SimulationRunClosed
  → ConsensusAnalysis derives records/minorities/packages (run-closed subscriber)
  → DecisionBrief projects the closed run with history, consensus and provenance gates
```

### 5. Governance guard

```
agent output
  → InstitutionOnlyOutput guard chain
       GC-001 person reference
       GC-002 personal quotation
       GC-003 institution alias
       GC-004 unsupported fact
       GC-005 provenance completeness
  → ACCEPT / REWRITE / REJECT
  → violation record (one row per rule) + guarded text hash
  → only accepted/rewritten output reaches NegotiationSession
```

---

## Eventing and consistency

| Mechanism | Where | Guarantee |
|---|---|---|
| Domain events | aggregates (`domain/events.py`) | Emitted inside the transaction that changes state |
| Transactional outbox | `shared/outbox.py`, `shared/relay.py` | Event row commits with the aggregate; relay publishes later |
| In-process progress broker | SimulationOrchestration / NegotiationSession | SSE replay by `Last-Event-ID`; heartbeats while idle |
| Unit of Work | `shared/db.py` ambient transaction | One logical use case = one transaction |
| Projections | ConsensusAnalysis, DecisionBrief | Rebuildable from the run log; not input state |

PostgreSQL is the source of truth. The outbox is the only bridge from domain commits to external
effects; no code publishes an event before its aggregate commit succeeds.

---

## Deployment architecture

```
                    reverse proxy / TLS
                           │
              ┌────────────┴────────────┐
              ▼                         ▼
   ┌─────────────────────┐   ┌─────────────────────┐
   │ FastAPI instance    │   │ FastAPI instance    │
   │  routers + contexts │   │  routers + contexts │
   │  simulation worker  │   │  simulation worker  │
   └──────────┬──────────┘   └──────────┬──────────┘
              │                         │
              └────────────┬────────────┘
                           ▼
                ┌─────────────────────┐
                │ PostgreSQL 16 +     │
                │ pgvector            │
                │ + outbox/lease      │
                └─────────────────────┘
```

- One image runs both HTTP and the simulation worker. The worker uses a database lease so only one
  instance processes a job; horizontal scaling is safe at the job level.
- Memory persistence is refused outside `ENV=local`; PostgreSQL is the only production family.
- The Next.js app is deployed separately and proxies `/api/hps/*` to the API, injecting the API key
  server-side so browser clients never see it.

---

## Security boundaries

| Boundary | Enforcement | Where |
|---|---|---|
| Browser → Next.js proxy | server-side API-key injection, no key in client | `frontend/app/api/hps/[...path]/route.ts` |
| Client → API | API key + required scope per operation; demo mode localhost-only | IdentityAccess + `require_declared_scope` |
| API → domain | principal → `actor_id` at the edge; no key types in domain | IdentityAccess ACL |
| Agent output → persistence | governance guard chain before writes | GovernanceCompliance |
| Run reads | snapshot-scoped evidence; `Last-Event-ID` validated before streaming | EvidenceRetrieval, SSE routers |
| Secrets | LLM keys/base URLs from environment; never persisted or logged | `shared/config.py` |
| Person data | institutions only; person-attributed quotations non-citable | EvidenceCorpus + governance |

---

## Operational surface

| Endpoint | Purpose |
|---|---|
| `GET /healthz` | process liveness; answers while dependencies are down |
| `GET /readyz` | database, LLM provider/model, OCR availability, persistence, worker, governance/consensus/decision-brief wiring |
| `GET /metrics` | dependency-free in-process counters/histograms |
| `GET /docs` / `GET /openapi.json` | generated API contract |

Readiness is explicit: `llm: scripted|openai-compatible|azure_ai_foundry`, `ocr: available|absent`,
`governance_provenance_producer: close_round`, adapter-vs-`PERSISTENCE` degradation and the simulation
worker state are all reported. A deployment cannot look "ready" while a required collaborator is
unwired.

---

## Persistence and migrations

| Range | Owner |
|---|---|
| `0101`–`0105` | EvidenceCorpus documents, index, snapshots, ingestion runs/outcomes |
| `0104` | IdentityAccess API keys |
| `0201`–`0202` | StakeholderModel (0202 deferred: durable D-001) |
| `0301` | ClaimValidation |
| `0302`–`0304` | SimulationOrchestration jobs, leases, pause reasons |
| `0305` | GovernanceCompliance |
| `0401`–`0402` | NegotiationSession snapshot + append-only log |
| `0501` | ConsensusAnalysis projections |
| `0502` | DecisionBrief |

Table ownership follows the context prefix in ADR-002 (`evidence_corpus_document`,
`negotiation_session_run`, …), so a migration or query that crosses contexts is visible at a glance.

---

## Integration points

| Integration | Protocol | Owner | Notes |
|---|---|---|---|
| PostgreSQL | asyncpg / SQLAlchemy 2.x | `shared/db.py` | default and only production persistence |
| pgvector | PostgreSQL extension | EvidenceRetrieval | target-state HNSW index; current dense score is hashing-char3gram |
| LLM provider | HTTP `/chat/completions` | SimulationOrchestration | OpenAI-compatible or Azure AI Foundry; scripted local only |
| PDF extraction | in-process PyMuPDF | EvidenceCorpus | local paths; OCR only when no text layer |
| Tesseract | system binary | EvidenceCorpus | optional; `/readyz` reports absence and batches fail fast |
| SSE | `text/event-stream` | SimulationOrchestration + NegotiationSession | job progress and domain events; `Last-Event-ID` replay |
| Outbox relay | PostgreSQL rows | `shared/relay.py` | at-least-once external publication |

---

## Known boundaries and deferred work

- **StakeholderModel durable persistence** is D-001: migration `0202` exists but the SQLAlchemy
  family is not yet the default; see `.pi/architecture/DEFERRED.md`.
- **Dense retrieval** uses `hashing-char3gram-v1`, not a neural encoder; pgvector HNSW is target-state.
- **Governance person detection** is deterministic; no LLM sits on the guard path.
- **Memory persistence** is an explicit local/test family and is refused outside `ENV=local`.
- **Simulation scripted provider** is honest theatre: `[synthetic]` arguments and persona-derived
  stances, never prompt echoes or actor hashes.

---

## Canonical references

| Topic | Document |
|---|---|
| Pattern / boundaries | [ADR-001](../decisions/ADR-001-architecture-pattern.md) |
| Storage and table ownership | [ADR-002](../decisions/ADR-002-data-storage-strategy.md) |
| Cross-context communication | [ADR-003](../decisions/ADR-003-cross-context-communication.md) |
| API style | [ADR-004](../decisions/ADR-004-api-design.md) |
| Auth | [ADR-005](../decisions/ADR-005-authentication-authorization.md) |
| Metering | [ADR-006](../decisions/ADR-006-cost-tracking-usage-metering.md) |
| Governance rules | [ADR-007](../decisions/ADR-007-compliance-engine-architecture.md) |
| Modeling depth | [ADR-008](../decisions/ADR-008-proportional-modeling-depth.md) |
| Runtime wiring | [ADR-009](../decisions/ADR-009-runtime-wiring-multilang-judgment.md) |
| Context contracts | `.pi/architecture/modules/*.md` |
| Roadmap | `.pi/architecture/implementation-roadmap.md` |

---

*Last updated: 2026-11-06*
*Architecture version: 1.0 — implemented modular monolith*
