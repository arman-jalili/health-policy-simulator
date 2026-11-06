# Runbook: NegotiationSession

Canonical module: `.pi/architecture/modules/negotiation-session.md`
ADR: `.pi/architecture/decisions/ADR-015-negotiation-session-runtime-integration.md`

## Startup

1. The application shell (`shared/app.py`) builds every upstream container first, then
   `negotiation_session.composition.build_container` with all ACL ports bound.
2. `app.state.negotiation_session` is exposed and `negotiation_session_router` is mounted.
3. The container loads the nine registered institutions through StakeholderModel; a run binds the
   requested ids or the first twelve registered profiles.
4. No migration runs today: the memory repository family backs both configured persistence
   families (see *Known gaps*).
5. `/readyz` stays green; `GET /api/v1/runs/{run_id}` for an unknown id returns `404
   SIMULATION_RUN_NOT_FOUND`.

## Shutdown

- Stop accepting writes first (drain the load balancer). In-flight SSE streams end when the client
  disconnects or the process stops.
- The container is discarded with the process; runs are **not** durable until the SQLAlchemy
  adapters and migrations `0401`/`0402` land. Announce this before any restart in staging.

## Failure modes

| Symptom | Cause | Action |
|---|---|---|
| `GOVERNANCE_GUARD_UNAVAILABLE` (5xx) | guard port unbound | fix composition; writes must stay blocked — never bypass |
| `SIMULATION_RUN_NOT_FOUND` | run opened in another replica/process | re-open the run; memory family has no cross-process store |
| `PHASE_REGRESSION` | command after the phase moved on | read `GET /runs/{id}` and issue the command admissible in the current phase |
| `ROUND_STILL_OPEN` / `ROUND_CLOSE_GUARD_VIOLATION` | round closed early | record the missing turn/abstention, then close |
| `ROUND_LEARNING_MISSING` | close attempted without `RoundLearning` | capture learning first |
| `ROUND_CAP_EXCEEDED` | sixth `open_round` at `round_cap=5` | expected: the run is terminal; read `SimulationRunClosed` |
| `REVISION_WITHOUT_CAUSE` | reason cites nothing | cite an argument or evidence pack from this run |
| `ARGUMENT_WITHOUT_EVIDENCE` | no pack and no `unsupported` flag | attach evidence or mark unsupported |
| `DUPLICATE_TURN` / `TURN_NOT_AVAILABLE` | second turn on one topic or no floor | one turn per topic per round |
| `COALITION_WITHOUT_OFFER` | member never received/accepted an offer | record the offer first |
| `EVIDENCE_PACK_NOT_FOUND` | pack id is not a frozen pack in EvidenceRetrieval | use `${GET /api/v1/evidence-packs/{id}}` output ids |
| `400 BAD_REQUEST` on `/stream` | malformed `Last-Event-ID` | send the `id:` value from the last received frame |

## Observability

- Structured logs: `shared.log_setup` JSON events (`http_request`, `domain_event_dispatched`) carry
  `request_id`/`trace_id`; every negotiation command logs through the same request scope.
- Metrics: `shared.metrics.METRICS` exposes request count/duration and domain-event counters via
  `GET /metrics`; SSE disconnects are visible as closed streams.
- Tracing: `X-Request-ID` / `X-Trace-Id` propagate through `RequestContextMiddleware`.
- Rules: domain guard rejections are logged with their stable `code`; they are client errors, not
  incidents.

## Rollback

Remove the `negotiation_session_router` include and the container construction from
`shared/app.py`. No migration to downgrade today; the memory state disappears with the process.
Keep the proofing stage in CI so a silent unwiring fails the build.

## Verification

```bash
curl -sS -X POST localhost:8000/api/v1/runs \
  -H 'Content-Type: application/json' \
  -d '{"question":"How do we stabilise costs?","round_cap":3}'
# 202 {run_id, phase:"position_formation", mandate_hash, bound:[...]}

curl -sS localhost:8000/api/v1/runs/$RUN_ID/events      # ordered SimulationRunOpened …
curl -sSN localhost:8000/api/v1/runs/$RUN_ID/negotiation/stream     # id/event/data frames
bash .pi/scripts/ci/check_negotiation-session_contracts.sh   # 138 checks, 0 failures
```

## Known gaps

- SQLAlchemy run/event-log adapters and migrations `0401`/`0402` are deferred; the memory family is
  the only store. Restart loses runs; replay is proven in-process.
- `SelectRelevantStakeholders` uses a deterministic term match; an LLM-assisted selection is a
  later refinement behind the same service.
