# Runbook — ConsensusAnalysis

**Context:** derived projections over a closed run log.
**Canonical:** `.pi/architecture/modules/consensus-analysis.md`
**ADR:** `.pi/architecture/decisions/ADR-016-consensus-analysis-runtime-integration.md`

## What this context owns

Nothing that is an input. A consensus record, a compromise package, a scenario and an impact
assessment are **projections**: they are recomputed from the closed run log, and a rebuild must
reproduce them (invariant 1). Losing every row costs a replay, not data.

## Startup

```bash
hps-api            # or: uvicorn shared.app:create_app --factory
```

Boot is safe to fail: `build_container` raises when a required port is missing rather than starting a
container that cannot derive. Look for:

```
consensus_analysis_wired   persistence=memory estimation_bases=['assumed'] note="..."
```

`estimation_bases=['assumed']` is expected today: `measured`, `derived` and `modelled` have no
calculation and refuse.

### Readiness

`GET /readyz` reports:

| Check | Meaning |
|---|---|
| `consensus_analysis: ok` | the container is mounted and the projection store answers |
| `consensus_analysis_projection: memory\|postgres` | which adapter is serving the projection |

A projection store is always "ok": what can be missing are the **inputs**, and a missing input is a
named refusal on the derivation path, not a broken probe.

## The expected refusal

```
POST /api/v1/runs/{run_id}/analysis:derive  →  503
{"code": "CONSENSUS_ANALYSIS_UNAVAILABLE", "message": "...", "trace_id": "..."}
```

Three messages, three meanings:

| Message contains | Meaning | Fix |
|---|---|---|
| `mandate threshold` | no per-run threshold is published | publish the mandate threshold for the run |
| `run-log read model` | no log adapter is wired | wire `RunLogPort` to the run log |
| `veto rights` | no bulk veto read model | wire `StakeholderPowersPort` |

**Do not work around any of these.** An empty agenda reports "nothing agreed", a default threshold is
a default quorum, and an empty veto map restores consensus for a class an institution can block. All
three manufacture agreement.

## Reading the projection

```bash
curl -s localhost:8000/api/v1/runs/$RUN/consensus | jq
curl -s localhost:8000/api/v1/runs/$RUN/conflicts/open | jq
curl -s localhost:8000/api/v1/runs/$RUN/packages | jq
```

`records: []` for a run that never closed is correct, not an error.

## Rebuild

The operator command replays the log and **proves** the rows are reproducible; it refuses to write
unless the replay equals the projection.

```python
from consensus_analysis.application.commands import RebuildProjectionsRequest

result = await container.rebuild_projections.execute(RebuildProjectionsRequest(run_id=run_id))
result.records, result.digest
```

| Symptom | Meaning | Action |
|---|---|---|
| `PROJECTION_REBUILD_FAILED: ... has no projection rows` | nothing to verify | derive first, then rebuild |
| `... holds N mandate thresholds` | the projection mixes mandates | investigate the writer; one run carries one mandate |
| `replayed rows differ ...: <topic>: ...` | the projection drifted | trust the log: rebuild with `verify_only=False` after confirming the log |

`verify_only=True` never writes — use it in an incident before replacing anything.

## What is deliberately not built yet

| Gap | Why it is safe | Trigger to close it |
|---|---|---|
| PostgreSQL projection tables (migration `0501` stays reserved) | in-memory store is replaced wholesale by a rebuild | repository implementation |
| `measured`/`derived`/`modelled` estimators | a formula invented here is the defect the guard prevents | calculation issue |
| Run-closed subscription registration | without a log it can only refuse | run-log read model published |

## Shutdown

Nothing to drain: no background worker, no in-flight projection. `replaced` rows are written inside
one transaction, so a shutdown mid-derive leaves the previous projection intact.
