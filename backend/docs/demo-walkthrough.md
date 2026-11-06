# Demo walkthrough — empty deployment to published brief

This is the supported bootstrap sequence. It requires one local sample PDF (`samples/demo-corpus.pdf`,
shipped in the repository), a reachable PostgreSQL database and the backend `.venv`. No Python
snippet and no manual provenance call is part of the sequence.

## 1. Configure and migrate

```bash
cd backend
source .venv/bin/activate

export ENV=local
export AUTH_MODE=demo
export PERSISTENCE=postgres
export DATABASE_URL="postgresql+asyncpg://hps:hps@localhost:5433/health_policy"
# Step 2 pipes the seed's stdout into a JSON file; at INFO the log records land there too (#419).
export LOG_LEVEL=ERROR

alembic upgrade head
```

`demo-seed` is refused outside `ENV=local`.

## 2. Seed the demo corpus (idempotent)

```bash
make demo-seed | tee /tmp/demo-seed.json
```

The command ingests `samples/demo-corpus.pdf`, publishes one citable passage per sample article,
pins the `demo-corpus-v1` snapshot, registers five reference figures and assembles one evidence pack
per demo topic. Re-running it reuses the same document, snapshot, figures and packs; it creates no
duplicate rows.

The JSON output contains the ids the walkthrough needs. The Kassenstellen pack is used below:

```json
{
  "document_id": "doc_…",
  "snapshot_id": "snp_…",
  "figure_ids": ["fig_…"],
  "pack_ids": {
    "kassenstellen": "evp_…",
    "spitalsreform": "evp_…",
    "pflegepersonal": "evp_…",
    "arzneimittelpreise": "evp_…",
    "digitalisierung": "evp_…"
  },
  "topics": [
    {"slug": "kassenstellen", "claim": "Die Kassenstellen sollen ausgebaut werden."}
  ]
}
```

## 3. Start the API

```bash
.venv/bin/python -m uvicorn shared.app:create_app --factory \
  --host 127.0.0.1 --port 8000
```

In another shell, set the base URL and the pack id from step 2:

```bash
export BASE=http://127.0.0.1:8000
export PACK_ID=evp_…            # pack_ids.kassenstellen from /tmp/demo-seed.json
```

## 4. Run the chain

### 4.1 Institutions

```bash
curl -s "$BASE/api/v1/stakeholders"
```

Expected `200`. The response lists nine institutional stakeholders. Use their `stakeholder_id`
values in the next call.

### 4.2 Open a run and its first round

```bash
curl -s -X POST "$BASE/api/v1/runs" \
  -H 'Content-Type: application/json' \
  -d '{
    "question": "Wie sichern wir Kassenstellen und Versorgung in Oesterreich?",
    "round_cap": 1,
    "stakeholder_ids": ["stk_aerztekammer", "stk_apothekerkammer", "stk_bmsgpk",
      "stk_krankenhausgesellschaft", "stk_landesgesundheitsfonds", "stk_oegk",
      "stk_patientenanwaltschaft", "stk_privatkrankenanstalten", "stk_sozialversicherung"]
  }'
```

Expected `202`; copy `run_id`.

```bash
export RUN_ID=run_…
curl -s -X POST "$BASE/api/v1/runs/$RUN_ID/rounds"
```

Expected `201`, `round: 1`.

### 4.3 Nine evidenced positions and turns

Repeat this pair once per stakeholder. The claim text is deliberately legal: the reference corpus
has no evidence pack for a legal provision, so ClaimValidation returns the truthful `unsupported`
verdict, which is admissible; an `ambiguous` verdict is not.

```bash
curl -s -X POST "$BASE/api/v1/runs/$RUN_ID/positions" \
  -H 'Content-Type: application/json' \
  -d '{
    "stakeholder_id": "stk_aerztekammer",
    "topic": "Kassenstellen",
    "stance": "support",
    "proposal": {"summary": "Kassenstellen ausbauen und Versorgung sichern"},
    "evidence_ids": ["'"$PACK_ID"'"]
  }'
```

Expected `201`. Copy `position_id` if you want to inspect the disclosure later.

```bash
curl -s -X POST "$BASE/api/v1/runs/$RUN_ID/turns" \
  -H 'Content-Type: application/json' \
  -d '{
    "stakeholder_id": "stk_aerztekammer",
    "target": {"topic": "Kassenstellen"},
    "stance": "support",
    "text": "Das ASVG regelt die Kassenstellen und die Finanzierung.",
    "claims": [{"text": "Das ASVG regelt die Kassenstellen."}],
    "evidence_ids": ["'"$PACK_ID"'"],
    "invocation_id": "inv_demo_01"
  }'
```

Expected `201`. Increment `invocation_id` for each turn.

### 4.4 Close the round

```bash
curl -s -X POST "$BASE/api/v1/runs/$RUN_ID/rounds/1:close" \
  -H 'Content-Type: application/json' \
  -d '{"learning": [], "convergence": "none"}'
```

Expected `200`, `stopping_condition.name = "round_cap"`, `fired: true`. Closing the run writes one
provenance disclosure per open position inside the same close transaction and triggers consensus
derivation; there is no separate provenance call.

```bash
curl -s "$BASE/api/v1/runs/$RUN_ID/consensus"
```

Expected `200` with at least one derived record. A closed run where everyone abstained is also
`200`: the record has `outcome: "unresolved"`, `support: 0.0` and
`reason: "no_recorded_stances"` — a domain outcome, not a `503`.

### 4.5 Publish the brief

```bash
curl -s -X POST "$BASE/api/v1/runs/$RUN_ID/brief"
```

Expected `201`, `version.number = 1`, eight sections and a simulation disclaimer.

```bash
curl -s "$BASE/api/v1/runs/$RUN_ID/briefs"
```

Expected `200` with one version.

## 5. Readiness posture

```bash
curl -s "$BASE/readyz"
```

The response includes:

- `negotiation_session: ok` and the actual persistence adapter;
- `consensus_analysis: ok` with `consensus_analysis_sources: wired`;
- `decision_brief: ok` and `decision_brief_gates: wired`;
- `governance_provenance: wired` and `governance_provenance_producer: close_round`;
- `attribution: client-declared`.

**Attribution posture (documented, W8):** every argument must carry a non-blank `invocation_id`
(ADR-006), but NegotiationSession does not yet resolve that id against an orchestrator usage store,
so a non-blank id that never existed on the run is accepted. This is client-declared attribution,
reported by `/readyz` instead of a validating-looking stub. The W8 entry in
`.pi/architecture/modules/negotiation-session.md` records the gap; closing it requires a
run-scoped invocation lookup in SimulationOrchestration, not a format check.

## 6. Automated version

```bash
make demo-walkthrough
```

This runs `alembic upgrade head`, the idempotent seed, starts the API on port 8010, drives the full
sequence over HTTP and prints the run, position, argument and brief ids. `stage_demo_walkthrough.sh`
runs the same target from local CI when `DATABASE_URL` is set.
