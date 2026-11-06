# DR plan — ConsensusAnalysis

**Context:** derived projections. **RPO:** zero for stored data — there is none. **RTO:** one replay.

## Recovery thesis

This context holds **no input state**. Every row is a function of (closed run log, mandate threshold,
veto map). Disaster recovery is therefore:

1. restore the run log (owned by NegotiationSession) and the stakeholder powers (StakeholderModel);
2. replay;
3. compare digests with whatever copy of the projection survived.

If nothing survived, the replay *is* the recovery: there is no authoritative copy to lose.

## Scenarios

| Scenario | Impact | Recovery |
|---|---|---|
| Projection rows lost (bad deploy, dropped table) | reads return `[]` | derive every run from the log |
| Projection drifted (partial write, manual edit) | `PROJECTION_REBUILD_FAILED` names the topic | `verify_only=True` to confirm, then rebuild |
| Log available, mandate unavailable | derivation refuses with `mandate threshold` | restore the mandate source |
| Log lost | **cannot be recovered here** | restore NegotiationSession's log (its own DR plan); this context is a pure consumer |
| Two projections disagree across regions | the digest decides | trust the one matching the replay |

## Verification after recovery

```bash
bash .pi/scripts/ci/check_consensus-analysis_contracts.sh     # 129 contract checks
pytest tests/unit/consensus-analysis -q                        # 167 behavioural proofs
pytest tests/integration/test_consensus_e2e.py -q              # mounted and fails closed
```

A rebuild that reports the same `digest` for the same run twice is the acceptance proof
(`test_rebuilding_twice_yields_byte_identical_records`).

## What is not recoverable here

In-memory persistence means a **process restart loses the projection**, by design. That is a cache
invalidation, not data loss: derive again. The PostgreSQL adapter (migration `0501`, still reserved)
changes the recovery time, never the recovery procedure.

## Escalation

1. Reads empty → is the run closed? (`GET /api/v1/runs/{run_id}` on NegotiationSession)
2. Derive refuses → read the message; it names the missing input, not a stack trace.
3. Rebuild mismatches → keep the log, capture the drift message, replace the projection.
4. Anything else → the module doc's Wiring Contract table maps each collaborator to its observable
   effect; the missing one is the incident.
