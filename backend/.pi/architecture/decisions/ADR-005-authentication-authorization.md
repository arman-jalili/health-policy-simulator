# ADR-005: Authentication & Authorization

**Status:** Accepted
**Date:** 2026-11-05
**Session:** 87433e56-b1a2-4464-a232-2dc4fe6f9dfd

## Context

The product is a policy-analysis tool used by analysts and operators, demoed to a jury.
Three roles exist in the exploration: **analyst** (creates and reads simulations),
**operator** (manages corpus ingestion and source authority curation), **admin** (configuration).
A full identity provider would consume hackathon time that the negotiation engine needs.

At the same time, the transparency requirement means published briefs are auditable artefacts:
we must know who triggered a run and who published a brief, even in a prototype.

## Decision

**API keys with scopes, resolved to a principal, with an explicit demo mode.**

| Concern | Decision |
|---|---|
| Mechanism | Static API keys (header `X-API-Key`), hashed at rest (SHA-256 + salt) |
| Principal | `{key_id, role, scopes, label}` — no user table, no passwords |
| Scopes | `runs:write`, `runs:read`, `corpus:write`, `corpus:read`, `briefs:publish`, `admin` |
| Roles → scopes | analyst: runs:*, briefs:read · operator: + corpus:*, briefs:publish · admin: `*` |
| Enforcement | FastAPI dependency guard per route; scope check declared in the route signature |
| Demo mode | `AUTH_MODE=demo` allows anonymous **read** + `runs:write` from localhost only; refused when `AUTH_MODE=strict` |
| Attribution | Every command records `actor` (key label or `demo`) on the outbox event and audit rows |
| Transport | HTTPS required outside localhost; keys never logged; `Authorization` redacted in traces |

**Why not JWT/OIDC:** a token issuer adds a service, a key-rotation story and a login screen that
the jury will never see. API keys give the same *authorisation* shape with a fraction of the work,
and the guard interface is where OIDC plugs in later without touching domain code.

**Why not open access:** the corpus is third-party press material and briefs are attributed
artefacts. "Who published this" must have an answer, even a demo one.

**Anti-corruption edge:** the auth layer yields a `Principal` value object; the domain never sees
API keys. Handlers translate `Principal → actor_id` before invoking an application service.

## Consequences

- Keys are manually provisioned in `.env` for the demo; rotation is a redeploy.
- No per-user preferences or sharing — acceptable at this scope.
- Demo mode must be impossible to enable accidentally in a public deployment (explicit env +
  startup warning + refusal to boot with `AUTH_MODE=demo` when `ENV=production`).
- Migration path: replace the `Principal` resolver with OIDC claims; scopes map to roles.

## Alternatives Considered

| Alternative | Why rejected |
|---|---|
| Keycloak / OIDC | Service to run, login UI to build, zero demo value |
| JWT with local issuer | We would be building the thing we rejected, smaller |
| No auth at all | Loses attribution on published briefs and corpus mutation |
| Session cookies | Browser-oriented; the frontend is one SPA and scripts use curl during demos |

## Affected Modules

IdentityAccess (adapter), SimulationOrchestration, EvidenceCorpus, DecisionBrief, GovernanceCompliance
