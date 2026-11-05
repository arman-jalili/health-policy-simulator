# Runbook — ClaimValidation

Operational procedures for the claim verifier. Canonical architecture:
`.pi/architecture/modules/claim-validation.md`; runtime decision:
`.pi/architecture/decisions/ADR-012-claim-validation-runtime-integration.md`.

## Service shape

| Item | Value |
|---|---|
| Entry path | `shared.app.create_app` → `claim_validation.composition.build_container` → router |
| Public API | `/api/v1/claims:verify`, `/claims/{id}:flag`, `/claims/{id}`, `/reference-figures`, `/contradictions`, `/claims/{id}/reviews` |
| Persistence | Migration `0301_claim_validation`: `claim_validation_claim`, `claim_validation_reference_figure`, `claim_validation_contradiction` |
| Memory mode | explicit `PERSISTENCE=memory`; test/local only |
| Readiness | `/readyz` reports `claim_validation` and `claim_validation_persistence` |
| Metrics | `claim_verifications_total`, `claim_reads_total`, `reference_figures_registered_total` |
| Logs | structlog JSON; boot event `claim_validation_wired` |

## Startup sequence

1. `uv run alembic upgrade head` — must reach `0301_claim_validation`.
2. Start `hps-api`.
3. `GET /healthz` → 200.
4. `GET /readyz` → 200 with `checks.claim_validation == "ok"` and
   `checks.claim_validation_persistence == "postgres"` (or `"memory"` locally).
5. `GET /api/v1/reference-figures` → 200. An **empty list is valid**; quantitative claims will be
   `AMBIGUOUS` until authoritative figures are registered.

## Registering authoritative reference figures

Only non-press tiers are accepted: `official_statistics`, `legislation`, `scientific_study`,
`institutional_statement`. `press_report`, negative values and missing source ids are refused with
`REFERENCE_FIGURE_NOT_AUTHORITATIVE` / `VALIDATION_FAILED`.

```bash
curl -s -X POST localhost:8000/api/v1/reference-figures \
  -H 'Content-Type: application/json' \
  -H "X-API-Key: $ADMIN_KEY" \
  -d '{"measure":{"measure":"Kassenstellen","unit":"count","period":"2026","geography":"AT"},
       "value":"1204","tier":"official_statistics","as_of":"2026-01-01",
       "source_id":"statistik_austria"}'
```

The table is deliberately not seeded with invented values. Empty data must produce `AMBIGUOUS`,
never `VERIFIED`.

## Common failure modes

| Symptom | Cause | Recovery |
|---|---|---|
| Quantitative claim returns `ambiguous` | No reference figure for the exact measure key | Register the figure; check measure/unit/period/geography |
| `REFERENCE_FIGURE_NOT_AUTHORITATIVE` | Press tier submitted | Use an authoritative tier |
| `PATH_NOT_APPLICABLE` | `claim_type` and requested path disagree | Send the correct `claim_type`; do not force a path |
| `REVIEW_NOT_ESCALATED` | Review submitted for a non-ambiguous claim | Escalate first; review only settles ambiguity |
| `CLAIM_NOT_FOUND` | Unknown claim id or wrong database | Check migration and `DATABASE_URL` |
| Legal claim stays `unsupported` | No provision evidence published yet | Supply evidence; never edit the verdict directly |
| Causal claim never `verified` | By design | Read `CausalClaimAppraised` support; never present as fact |
| `/readyz` red | Database unreachable | Restore DB connectivity; process stays live but not ready |

## Incident response and escalation

1. Capture claim id, measure key, verdict, trace id and the reference figure used.
2. If a wrong verdict is suspected, stop accepting new arguments; keep the audit rows.
3. Reproduce with `GET /claims/{id}` and `GET /reference-figures`.
4. Fix the reference figure or evidence, then re-verify; never mutate a stored verdict in SQL.
5. Add a regression test before closing the incident.
6. Escalate to the single prototype owner.

## Rollback

| Layer | Action |
|---|---|
| Process | Redeploy previous image |
| Schema | `alembic downgrade 0201_evidence_retrieval` (drops claim-validation tables) |
| Data | Restore the pre-change dump before downgrading if claims must be retained |
| Code | Revert the MR |
