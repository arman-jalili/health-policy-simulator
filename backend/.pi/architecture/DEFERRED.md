# Deferred Work

> Deliberately postponed items, with the decision already made and the cost known.
> Not an issue tracker: this file is the record for work that is **accepted as incomplete**
> and will be picked up when the sequencing allows.
>
> Rule: nothing leaves this file by being forgotten. An item is closed by being implemented,
> or by a new decision recorded here.

---

## D-001 — StakeholderModel durable persistence

**Status:** Deferred (accepted for the demo)
**Owner:** unassigned
**Recorded:** 2026-11-06 · epic stakeholder-model (#101), `main @ af6b87e`
**Estimate:** ~3–3.5 h (Option A) · ~7–9 h (Option B) · agent time

### What is true today

| Aspect | State |
|---|---|
| Persona cards | 9 validated YAMLs in `config/personas/`, loaded and fail-fast-validated at boot |
| Registry | `InMemoryStakeholderRepository` seeded from those cards |
| Mutable state | profile edits, `HistoricalPosition`, `MandateSource` additions, `AgentBinding` — **all in memory, lost on restart** |
| Persistence switch | `PERSISTENCE` is read but ignored for stakeholder state: memory is used even under `PERSISTENCE=postgres` |
| Signal | boot warning `stakeholder_profiles_in_memory`; **`/readyz` reports `stakeholder_model: ok`** |
| ADR | ADR-011 records the limitation but does not name ADR-002 (which it deviates from) and sets no exit criterion |

### Why it was accepted

The demo reads personas (durable in git) and does not depend on surviving a restart. The cost of
persisting was deferred in favour of finishing the negotiation path.

### Why it must not stay deferred forever

`NegotiationSession` will consume `HistoricalPosition` as evidence of institutional history. A
restart that silently deletes history turns evidence into a prompt decoration. The trigger to
implement is therefore concrete, not calendar-based:

> **Revisit before any run where API-registered history must influence a negotiation outcome** —
> i.e. the first time `SubmitInitialPosition` or `TakeNegotiationTurn` cites a `HistoricalPosition`.

### Recommended implementation (Option A — JSONB per aggregate)

Two tables, one migration, no join logic:

```sql
-- migrations/versions/0202_stakeholder_model.py
stakeholder (
  id, code, identity jsonb, profile jsonb, history jsonb,
  veto_rights jsonb, dependencies jsonb, profile_version, updated_at
)
agent_binding (
  run_id, stakeholder_id, payload jsonb, persona_version, created_at
)
```

Option B (normalised: `interest`, `constraint`, `priority`, `veto_right`, `dependency`,
`historical_position` as child tables) is **only** justified if negotiation needs to query history by
topic/date in SQL. Decide that when the negotiation query shape is known; do not normalise speculatively.

### The one open decision — seed reconciliation

Personas load at boot and seed the registry. With a durable registry, boot must not clobber
operator edits. Pick one **before** writing code:

| Strategy | Behaviour | Cost | Verdict |
|---|---|---|---|
| Insert-if-absent | Seed only when `code` missing; YAML changes need manual migration | lowest | safe fallback |
| **Upsert on `persona_version` bump** | Seed overwrites only when the YAML version changes, else DB wins | +~30 lines | **recommended** |
| YAML is truth, DB is cache | Re-seed every boot, edits discarded | lowest | only if write endpoints are declared read-only |

`persona_version` already exists in every persona YAML, so strategy 2 costs almost nothing and makes
the field do real work.

### Acceptance criteria (mirror the corpus precedent, issue #26)

- [ ] `PERSISTENCE=postgres` wires `SqlAlchemyStakeholderRepository` + `SqlAlchemyAgentBindingRepository`
- [ ] `PERSISTENCE=memory` still works for tests; memory remains refused outside `ENV=local`
- [ ] `alembic upgrade head` on an empty DB creates every queried table; `downgrade base` reverses it
- [ ] Restart round-trip: register a profile edit + a `HistoricalPosition`, restart the process, both are still there
- [ ] `AgentBinding` remains immutable across the round-trip
- [ ] Weak attribution (`usable = false`) survives persistence and still cannot override an explicit statement
- [ ] Boot seed is idempotent: two consecutive boots produce no duplicate rows and no version churn
- [ ] `/readyz` gains `stakeholder_model_persistence`: `postgres` vs `memory`, and reports **degraded** (not `ok`) when the DB is configured but stakeholder state is in memory
- [ ] Proofing script gains the durability checks; integration test follows `test_corpus_persistence.py`
- [ ] ADR-011 amended: name ADR-002 as the deviation, record the exit criterion above

### Files that will change

```
migrations/versions/0202_stakeholder_model.py          (new)
src/stakeholder_model/infrastructure/repository/models.py       (new)
src/stakeholder_model/infrastructure/repository/sqlalchemy.py   (new)
src/stakeholder_model/composition.py                   (adapter switch + seed reconciliation)
src/shared/http/health.py                              (persistence flag)
src/shared/config.py                                   (only if a settings field is added)
tests/integration/test_stakeholder_persistence.py      (new, model on corpus)
.pi/scripts/ci/check_stakeholder-model_contracts.sh    (durability checks)
.pi/architecture/decisions/ADR-011-*.md, modules/stakeholder-model.md, docs/runbook-*.md, docs/dr-plan-*.md
```

### Reusable groundwork (already exists)

- `shared.db.UnitOfWork` — already constructed inside this module's composition
- `docs/runbook-stakeholder-model.md` § durability, `docs/dr-plan-stakeholder-model.md` — already state the gap
- `tests/integration/test_corpus_persistence.py` (403 lines) — copy-paste skeleton for restart proofs
- `migrations/versions/0101_evidence_corpus_documents.py` (148 lines) — migration template

---

## D-005 — GovernanceCompliance provenance facts source

**Status:** Closed by #407 (position/evidence/argument facts + invocation/model reference)
**Recorded:** 2026-11-06 · governance-compliance epic (#269)
**Estimate:** ~2 h once NegotiationSession exposes position/argument/run-log reads.

`DisclosePositionProvenance` is wired to a stub `ProvenanceFactsSource` that returns empty facts, so
`POST /positions/{id}/provenance` always returns `PROVENANCE_INCOMPLETE`. That is fail-closed, but no
caller can satisfy it. Boot logs `governance_provenance_source_deferred` and `/readyz` reports
`governance_provenance: deferred`.

**Exit criterion:** bind a real adapter that reads evidence + argument ids from NegotiationSession,
invocation/prompt/model from SimulationOrchestration, and claim verdicts from ClaimValidation. Replace
the stub, remove the `deferred` readyz value, and add the public E2E disclosure test named in the module
W8 table.

**Closed:** `NegotiationProvenanceFacts` reads the aggregate by position id, takes evidence/argument ids
and the argument's invocation, and `/readyz` reports `governance_provenance: wired`.

---

## Also accepted for the demo (smaller, same treatment)

| ID | Item | Cost | Risk if left |
|---|---|---|---|
| D-002 | Verify the nine `MandateSource.citation` strings against legal sources; `citation` is only validated as non-empty text | ~30 min manual | A wrong § is worse than no § if a juror spot-checks: `patientenanwaltschaft` → "Patientenverfügungsgesetz, § 1" and `oegk` → "§ 23 ASVG" look incorrect |
| D-003 | Retrieval evaluation set lacks paraphrase/synonym cases (issue #99 follow-up). Current artifact: lexical 0.20 → hybrid 1.00 on 50 near-identical synthetic strings | ~2 h (write 15 cases) | The delta measures digit discrimination, not semantic recall; do not quote it as retrieval quality |
| D-004 | `semantic` score comes from `hashing-char3gram-v1` (morphology-aware fuzzy match), not a neural encoder | ~half day (bind encoder + pgvector HNSW) | Field name invites overclaiming; honest label is "semantic (hashing)" |

## D-010 — Operator task: ingest the 3 GB PDF corpus

**Status:** Deferred (not started; operator chore, no code change expected)
**Owner:** operator (Arman)
**Recorded:** 2026-11-06 · `main @ a309c11`
**Estimate:** 1 h setup + unattended runtime (measure on one document first)
**Runbook:** `docs/corpus-ingestion.md` · **tool:** `scripts/ingest_corpus.py` · **blocks:** nothing in CI

### Why it is not done yet

The user has a ~3 GB PDF corpus and will ingest it after the frontend is built. Nothing in the repository is
waiting on it: the demo runs on `demo-corpus-v1` (one sample PDF, five topics). This entry exists so the task
is not lost — the register is read by anyone opening the module docs, the issue tracker is not.

### What is true today

| Aspect | State |
|---|---|
| Ingestion over HTTP | **impossible for a corpus** — `POST /corpus/documents` extracts only; segmentation and indexing have no route (**#424**), `POST /corpus/ingestion-runs` only records a row |
| Working path | `scripts/ingest_corpus.py` (offline, resumable, per-document commit, paragraph chunking, snapshot pin); verified end to end against a migrated database |
| Corpus in the repo | `samples/demo-corpus.pdf` only (3 pages); `make demo-seed` pins `demo-corpus-v1` with 5 topics, 5 reference figures, 5 packs |
| Existing packs | reference `demo-corpus-v1` — a new corpus needs new packs and a new seed JSON for the frontend |

### Steps (carry them out in this order)

1. **Run the backend suite first, not after**: `pytest -m integration` executes `alembic downgrade base` on
   `DATABASE_URL` and wipes the database (**#421**). Ingest is the last step before a demo.
2. Check for scans (`chars/page ≈ 0` ⇒ OCR at seconds per page, a different job) — snippet in the runbook.
3. Split monoliths (`qpdf --split-pages=200`); target 20–80 MB / 100–500 pages per file.
4. `python scripts/ingest_corpus.py material/ --snapshot-label corpus-2026 --dry-run`, then `--limit 10` to
   measure the rate, then the full run under `nohup`.
5. Assemble packs against the printed `snapshot_id` (`POST /evidence/packs`), or ingest a curated
   `material/demo/` into its own `demo-corpus-v2` snapshot for the jury run.
6. Update the seed JSON the frontend imports (`/settings → Demo-Bootstrap`) or re-run `make demo-seed`.

### Exit criterion

A pack assembled against the new snapshot returns passages from the ingested PDFs, and a run uses that pack for
all nine positions. Then delete this entry and note the snapshot label here.

---

## Closed deferrals

| ID | Item | Closed by |
|---|---|---|
| — | (none yet) | — |

---

*Canonical: `.pi/architecture/DEFERRED.md`. Referenced from ADR-011, the stakeholder-model module doc
and the implementation roadmap's post-hackathon section.*

---

## D-008 — NegotiationSession durable persistence

**Status:** Closed by #405 (migrations 0401/0402 + SQLAlchemy adapters + restart test)
**Recorded:** 2026-11-06 · epic negotiation-session (#281), `main @ ef2ceb4`
**Estimate:** ~4–5 h

| Aspect | State |
|---|---|
| Migrations | `0401`/`0402` are pre-allocated stubs with **no** `create_table` |
| Adapters | `InMemorySimulationRunRepository` / `InMemoryRunEventLog` for **both** `PERSISTENCE` families |
| Durability | a run created under `PERSISTENCE=postgres` returns `404` after a restart (verified) |
| Readiness | `/readyz` does not report the module at all |
| Gates violated | W2 (memory as the silent default), W3 (no migration owns the tables), W7 (no restart round-trip) |

**Trigger:** the first demo or test where a negotiation must span a restart, or the moment Phase 5's
projection rebuild is exercised on stored runs. Rebuilding a projection from an event log that does not
survive a restart is not a rebuild.

**Closed:** `0401` stores the aggregate snapshot and child tables; `0402` stores the append-only log with
store-allocated ordinals. `build_negotiation_container` selects the adapters by `PERSISTENCE`; a run and
its event log survive an engine dispose + fresh container.

---

## D-009 — NegotiationSession → ConsensusAnalysis seam

**Status:** Closed by #406 (run-log, powers and mandate ACLs; run-closed subscriber; 0501 adapters)
**Recorded:** 2026-11-06 · epics negotiation-session (#281) + consensus-analysis (#304)
**Estimate:** ~6–8 h (three ports + one subscription + `0501` adapters)

| Port | Today |
|---|---|
| `RunLogPort` (agenda, stances) | `unavailable_run_log()` → derivation refuses |
| `StakeholderPowersPort` (veto classes, power) | `unavailable_powers()` |
| `MandateThresholdSource` (per-run threshold) | `unavailable_mandate()` |
| `HandleRunClosed` | constructed, **never subscribed and never invoked** |
| Consensus repositories | in-memory; migration `0501` is a stub |

**Trigger:** closing the first run that should produce a consensus record. Until then
`POST /runs/{id}/analysis:derive` answers `503 CONSENSUS_ANALYSIS_UNAVAILABLE`, which is honest — but it is
a dependency gap, not a verdict.

**Closed:** the runtime binds `NegotiationRunLogSource`, `NegotiationStakeholderPowers` and
`NegotiationMandateThreshold`; `CloseRound` notifies `HandleRunClosed`; `0501` gets a SQLAlchemy
repository. A missing run still fails closed with a named reason.

---

## D-007 — DecisionBrief upstream bindings

**Status:** Closed by #407 (history/consensus/provenance gates bound; 0502 + shared outbox).
**Verified 2026-11-06 (`adafc3b`):** a brief publishes (`201`) and lists one version — but only after a
manual `POST /positions/{id}/provenance` per position, because no negotiation use case wrote the
disclosure record the gate reads. **Closed by #412:** `CloseRound` now discloses every open position in
the close transaction; the explicit route remains for re-disclosure.
**Owner:** consensus-analysis epic + governance-compliance epic
**Recorded:** 2026-11-06 · epic decision-brief (#330), issue #346
**Estimate:** 4–6 h once the two upstream contexts publish the missing reads

### What is true today

| Aspect | State |
|---|---|
| Router, container, publication use case | mounted in `shared/app.py`; `POST /api/v1/runs/{id}/brief` reaches the real use case |
| Projection builder | real (`BriefProjectionAdapter` + `SectionAssembler`) |
| Citation resolver | real (`EvidenceCorpusCitationResolver` over `corpus.resolve_passage`) |
| Run-history port | **unwired** (`UnwiredHistorySource`) — NegotiationSession publishes run state, round summaries and conflict topics but no question text and no corpus snapshot pin, and `BriefVersion` requires both |
| Consensus port | bound to `ConsensusViewAcl` over the mounted consensus container |
| Provenance gate | bound to `GovernanceProvenanceGate` (all open positions must have a disclosure row) |
| Persistence | `SqlAlchemyDecisionBriefRepository` over `0502` when `PERSISTENCE=postgres` |
| Events | `SharedOutboxEventPublisher` writes `shared_event_outbox` |
| Signal | gated publication returns 201 only when every gate passes; missing run/citation/disclosure is 409/422 |

### Why it was accepted

Publication must fail closed rather than invent a question, a snapshot or a disclosure. Binding a
port to a fabricated value would defeat the epic's purpose (a brief that proves transparency).

### Exit criteria

1. NegotiationSession publishes `question` and the pinned corpus snapshot for a closed run.
2. ConsensusAnalysis is mounted at `app.state.consensus_analysis` and exposes `GetConsensus`.
3. GovernanceCompliance exposes disclosed provenance for all positions of a run (or the gate reads
   positions and checks each).
4. Migration `0502_decision_brief` gets its SQLAlchemy adapter and the events use the shared outbox.
