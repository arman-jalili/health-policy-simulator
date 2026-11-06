# Implementation plan — #277 / #278

## #277
1. `claim_validation/domain/services.py`: normalise `unit` using whitespace-collapsed casefold;
   map canonical values (`count`, `percent`, `days`, `EUR`) back to themselves.
2. Unit/property tests for casing, fixed point, idempotence, unknown-unit passthrough.
3. API test verifying a `Count` claim against a `count` reference figure.

## #278
1. Add `ProgressKind.STREAM_CLOSED`.
2. `StreamSimulationProgress` takes `idle_timeout_s` and `heartbeat_s`.
   - Replay known events; wait indefinitely up to max idle.
   - Yield raw `: ping\n\n` when idle.
   - Yield `run.stream_closed` as the last frame with `reason` (terminal or max_idle).
   - Replay after a terminal id returns immediately (no synthetic duplicate).
   - Increment `simulation_stream_disconnects_total` on cancellation/GeneratorExit.
3. `_sse` handles raw heartbeat strings and omits the `id:` line for the synthetic close marker.
4. Config: `SIMULATION_STREAM_IDLE_S` (default 3600), `SIMULATION_STREAM_HEARTBEAT_S` (default 15).
5. Tests: no old-cutoff close, heartbeat visible, marker last, disconnect stops polling.
6. Docs: configuration table, module SSE row, CHANGELOG.
