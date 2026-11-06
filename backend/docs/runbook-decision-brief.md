# Runbook: DecisionBrief

Canonical module: `.pi/architecture/modules/decision-brief.md`
Contracts: `docs/contracts-decision-brief.md`
Deferred bindings: `.pi/architecture/DEFERRED.md` **D-007**

## Startup

1. `PERSISTENCE=memory|postgres`, `DATABASE_URL` exported (the brief repository is in-memory until
   D-007 closes; the setting is validated by the shell, not by this context).
2. Boot builds the container: citation resolver over `EvidenceCorpus.ResolvePassage`, the JSON
   renderer, the projection adapter, the five use cases, and the in-memory repository.
3. `GET /readyz` reports `decision_brief` and `decision_brief_gates`:
   - `ok` + `wired` — every publication port is bound;
   - `degraded` + the unwired port names — at least one gate is fail-closed (current state: D-007).
     This is a deliberate state, not an outage, and readiness stays 200.
4. Log line `decision_brief_wired` names the persistence family and the bound collaborator classes.

## Endpoints

| Method | Path | Scope | Behaviour |
|---|---|---|---|
| POST | `/api/v1/runs/{run_id}/brief` | `briefs:publish` | project, gate, freeze version N |
| GET | `/api/v1/briefs/{brief_id}` | `runs:read` | read the frozen document |
| GET | `/api/v1/runs/{run_id}/briefs` | `runs:read` | versions with lineage |
| POST | `/api/v1/briefs/{brief_id}:version` | `briefs:publish` | successor N+1, prior superseded |
| GET | `/api/v1/briefs/{brief_id}/citations` | `runs:read` | citation + resolution state |

## Failure modes

| Symptom | Code | Cause | Action |
|---|---|---|---|
| 503 on publish | `BRIEF_GATE_UNAVAILABLE` | history, consensus or provenance port not bound (D-007) | close D-007; never bind a fake gate |
| 409 on publish | `BRIEF_SOURCE_INCOMPLETE` | run not closed / no derived consensus | finish the run; publish after close |
| 422 | `INCOMPLETE_BRIEF` | fewer than eight sections | fix the projection; the missing kinds are named |
| 422 | `UNRESOLVED_CITATION` | a citation did not resolve | check the passage exists in the pinned snapshot; publication is blocked and `CitationResolutionFailed` is recorded |
| 422 | `DISCLOSURE_MISSING` | rejected proposals or disclaimer absent | disclose the run's refusals; use `SimulationDisclaimer.canonical` |
| 422 | `STATEMENT_WITHOUT_CITATION` | `evidenced` statement without a passage | add the citation or mark it `narrative`/`unsupported` |
| 422 | `BLOCKED_OUTCOME_MISRENDERED` | a vetoed topic stated as consensus | state it `blocked` with the blockers |
| 409 | `PUBLISHED_BRIEF_IMMUTABLE` | in-place change of a published brief | create a version (`POST /briefs/{id}:version`) |
| 409 | `BRIEF_VERSION_CONFLICT` | successor is not N+1 / wrong prior / reason mismatch | rebuild the successor from N |
| 409 | `BRIEF_NOT_PUBLISHED` | versioning or listing citations of a draft | publish first |
| 404 | `BRIEF_NOT_FOUND` | unknown brief id | use the id returned by publication |
| 403 | `SCOPE_REQUIRED` | analyst key on a publish route | use a principal with `briefs:publish` |

A blocked publication leaves the brief `BLOCKED` with its audit events; fix the cause and retry.
A **published** brief is immutable — never "correct" it in place.

## Observability

- `decision_brief_wired` at boot (persistence, bound adapters), `decision_brief_event` for every
  published domain event (until the outbox binding lands with D-007).
- `GET /readyz` fields `decision_brief` / `decision_brief_gates` (see Startup).
- Request logs carry `trace_id`; error envelopes repeat it so a 5xx can be traced end to end.
- There is no decision-brief-specific counter yet: publication volume is visible in HTTP metrics by
  route and status. Add module counters with the persistence binding.

## Recovery

1. A draft/blocked brief is not stored persistently today (memory repository, D-007): a restart
   loses drafts. This is acceptable while publication is fail-closed; it is **not** acceptable when
   the gates are bound.
2. Regeneration is deterministic (`ReproductionCheck`): the same run log plus pinned snapshot
   reproduces the artefact, with narrative wording as the only allowed difference.
3. If a published brief is wrong, publish a successor with a reason; both versions stay retrievable.

## Verification

```bash
bash .pi/scripts/ci/check_decision-brief_contracts.sh          # 149 structural checks
bash .pi/scripts/ci/stage_decision-brief_proofing.sh           # + coverage gate (>= 80%)
PYTHONPATH=src pytest tests/unit/decision-brief -q
```

## Rollback

Remove `app.state.decision_brief` and `app.include_router(decision_brief_router)` and the module
becomes inert; no other context imports it. Migration `0502_decision_brief` is reserved and empty —
removing the router needs no schema rollback. **Never** roll back a published brief: withdraw it by
publishing a successor version.
