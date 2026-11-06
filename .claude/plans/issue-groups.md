# Issue groups — 2026-11-06

## Batch: `fix/427-429-runtime-honesty`

One branch because all three are the same failure mode: a capability existed but the observable
outcome was not honest (or not gated).

| Issue | Component | Type | Order |
|---|---|---|---|
| #427 | evidence-corpus ingestion | bug | 1 |
| #428 | CI architecture job | gap | 2 |
| #429 | simulation-orchestration scripted runtime | enhancement | 3 |

Dependency: #427 and #429 are independent; #428 is independent but should land in the same PR so
the new tests actually gate a merge.
