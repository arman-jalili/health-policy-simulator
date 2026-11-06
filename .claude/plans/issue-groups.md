# Issue Groups — 2026-11-06

| Group | Issues | Component | Branch | Order |
|---|---|---|---|---|
| Correctness batch | #277, #278 | claim-validation + simulation-orchestration | `fix/277-278-correctness` | #277 → #278 |

## #277 — measure identity casing
- Normalise the unit fallback (whitespace + casefold) and add canonical `count`, `percent`, `days`.
- Property test: emitted vocabulary is a fixed point and `resolve(resolve(x)) == resolve(x)`.
- API test: register `count`, verify with `Count`/`COUNT`.

## #278 — SSE liveness
- Remove the 0.5 s close; wait for a terminal event or configurable max idle.
- Emit `: ping` heartbeats and a final `run.stream_closed` marker with a reason.
- Close only on terminal/max-idle/client disconnect; count disconnects.
