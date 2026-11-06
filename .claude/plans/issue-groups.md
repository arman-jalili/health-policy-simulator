# Issue Groups — 2026-11-06 (round lifecycle / analysis chain)

| Group | Issues | Component | Branch | Order |
|---|---|---|---|---|
| Runtime chain | #404, #405, #406, #407, #408, #409 | negotiation-session → consensus-analysis → decision-brief → readiness/docs | `feat/404-409-runtime-chain` | #404 → #405 → #406 → #407 → #408 → #409 |

Dependency order is the run lifecycle itself: a run must open/close before the closed-run subscriber,
derived consensus, brief gates and readiness can be verified. #409 records the resulting state.
