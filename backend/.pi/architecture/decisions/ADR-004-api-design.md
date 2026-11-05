# ADR-004: API Design

**Status:** Accepted
**Date:** 2026-11-05
**Session:** 87433e56-b1a2-4464-a232-2dc4fe6f9dfd

## Context

The frontend must: create a simulation from a policy question, watch a negotiation unfold live,
inspect any argument's evidence, see why a position changed, and read the final brief. Two access
patterns dominate — **long-running mutation** (a run takes minutes) and **live observation**
(rounds stream as they commit).

## Decision

**REST + JSON under `/api/v1`, with Server-Sent Events for streaming. OpenAPI generated from
Pydantic models and treated as the contract.**

| Concern | Decision |
|---|---|
| Style | REST, resource-oriented, JSON only (no GraphQL) |
| Versioning | Path prefix `/api/v1`; additive changes stay in v1; breaking changes get `/v2` |
| Long-running work | `POST` returns `202 Accepted` + `run_id`; work proceeds on a worker; client polls or streams |
| Streaming | `GET /runs/{id}/stream` as `text/event-stream` (SSE), replayable via `Last-Event-ID` |
| Errors | Uniform envelope: `{code, message, details[], trace_id}`; stable machine codes |
| Pagination | Cursor-based (`?cursor=&limit=`) on history endpoints |
| Idempotency | `Idempotency-Key` header honoured on `POST /runs` and `POST /runs/{id}/resume` |
| Naming | Plural nouns, lowercase, hyphenated paths; snake_case JSON fields |
| Time | ISO-8601 UTC with `Z` |
| Money/numbers | Decimal strings, never floats, for figures that may appear in a brief |

**Degenerate-case policy (important for this domain):**
`200` with an explicit absence is preferred over `404` when the absence is meaningful.
A claim with no contradicting evidence returns `{"absence": true, "queries": [...], "reason": "..."}`
rather than an empty list, so the client can display "searched, found nothing" honestly.

**SSE event envelope**
```
event: round.opened | position.stated | argument.submitted | position.revised
     | conflict.opened | coalition.formed | round.closed | run.closed
id: <event_id>            (monotonic, supports Last-Event-ID replay)
data: {"run_id": "...", "round": 2, "sequence": 41, ...}
```

**Endpoint inventory (18):** runs (create/read/list/pause/resume/stream/events), positions,
arguments, conflicts, coalitions, evidence packs, passages, claims, stakeholders, briefs
(publish/read/versions), health.

## Consequences

- The frontend renders the negotiation from the event stream, not from polling diffs.
- SSE replay makes a dropped connection recoverable — essential for a live demo.
- REST keeps the surface inspectable with curl during the demo.
- No bidirectional channel, so interactive steering (mid-run steering of an agent) is out of scope.

## Alternatives Considered

| Alternative | Why rejected |
|---|---|
| WebSocket | Bidirectional complexity; we only need server→client |
| GraphQL | Over-modeling for 18 endpoints; cache/upload complexity |
| gRPC | Browser friction; no benefit for a single client |
| Polling only | Misses the "watch it happen" quality that the jury scores |

## Affected Modules

NegotiationSession, SimulationOrchestration, DecisionBrief, EvidenceRetrieval, EvidenceCorpus,
StakeholderModel, ConsensusAnalysis, ClaimValidation, GovernanceCompliance
