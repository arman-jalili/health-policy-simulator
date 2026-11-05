# ADR-006: Cost Tracking & Usage Metering

**Status:** Accepted
**Date:** 2026-11-05
**Session:** 87433e56-b1a2-4464-a232-2dc4fe6f9dfd

## Context

Every negotiation round calls an LLM several times (nine stakeholders × several turns). A run can
silently cost orders of magnitude more than expected, and a hackathon budget is finite. The
exploration also requires traceability: each argument must be explainable by the invocation that
produced it — model, prompt version, parameters, evidence pack, tokens.

Cost tracking is therefore **not** an afterthought: it is the same record that provides
reproducibility.

## Decision

**Meter every agent invocation as a first-class persisted record, and enforce a per-run budget.**

| Concern | Decision |
|---|---|
| Unit of metering | One `AgentInvocation` row per LLM call: context, run, round, stakeholder, purpose, model, prompt template id+version, temperature/max_tokens, evidence pack ids, input/output tokens, latency, cost estimate, outcome (`ok`/`error`/`rejected`) |
| Cost source | Provider price table in config (`models.yaml`), never hard-coded in code |
| Aggregation | `run.cost_summary` computed by query, not stored twice |
| Budget guard | `RunBudget` per run: `max_invocations`, `max_tokens`, `max_cost`. Checked **before** each call; on breach the run pauses with `budget_exhausted`, it does not silently degrade |
| Prompt versions | Prompt templates are files with `id@version`; the version string is persisted with the invocation |
| Failure accounting | Failed and governance-rejected calls are metered too — they cost tokens |
| Reporting | `GET /runs/{id}/usage` returns per-stakeholder and per-round breakdown; the brief may cite it |
| Streaming cost | SSE events carry a running cost counter for the live demo view |

**Budget breach is a domain event**, not an exception: `RunBudgetExhausted` pauses the run so the
operator can raise the limit and resume — the negotiation state is untouched.

## Consequences

- Full reproducibility envelope: model + prompt version + evidence + parameters per argument.
- The demo cannot accidentally burn the budget mid-presentation; it stops at a known point.
- Slight write amplification: one row per LLM call (hundreds per run — negligible).
- Price table needs maintenance when providers change; stale prices understate cost, so the
  table records `price_version` and the run records which version it used.

## Alternatives Considered

| Alternative | Why rejected |
|---|---|
| Provider dashboard only | Not per-run, not per-stakeholder, not joinable to arguments |
| Log-file metering | Not queryable, lost on restart, not transactional with the invocation |
| Token counting after the fact | Cannot pause before an overrun, only report it |
| Hard-coded prices | Silently wrong when providers change; unversioned |

## Affected Modules

SimulationOrchestration (owner), NegotiationSession (emits invocation-linked arguments),
GovernanceCompliance (rejections are metered), DecisionBrief (may cite usage), IdentityAccess (actor attribution)
