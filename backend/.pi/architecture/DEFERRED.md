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

## Also accepted for the demo (smaller, same treatment)

| ID | Item | Cost | Risk if left |
|---|---|---|---|
| D-002 | Verify the nine `MandateSource.citation` strings against legal sources; `citation` is only validated as non-empty text | ~30 min manual | A wrong § is worse than no § if a juror spot-checks: `patientenanwaltschaft` → "Patientenverfügungsgesetz, § 1" and `oegk` → "§ 23 ASVG" look incorrect |
| D-003 | Retrieval evaluation set lacks paraphrase/synonym cases (issue #99 follow-up). Current artifact: lexical 0.20 → hybrid 1.00 on 50 near-identical synthetic strings | ~2 h (write 15 cases) | The delta measures digit discrimination, not semantic recall; do not quote it as retrieval quality |
| D-004 | `semantic` score comes from `hashing-char3gram-v1` (morphology-aware fuzzy match), not a neural encoder | ~half day (bind encoder + pgvector HNSW) | Field name invites overclaiming; honest label is "semantic (hashing)" |

## Closed deferrals

| ID | Item | Closed by |
|---|---|---|
| — | (none yet) | — |

---

*Canonical: `.pi/architecture/DEFERRED.md`. Referenced from ADR-011, the stakeholder-model module doc
and the implementation roadmap's post-hackathon section.*
