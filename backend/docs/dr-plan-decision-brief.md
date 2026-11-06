# DR plan: DecisionBrief

Canonical: `docs/runbook-decision-brief.md`
Deferred bindings: `.pi/architecture/DEFERRED.md` **D-007**

## Targets

| Scenario | RTO | RPO |
|---|---:|---:|
| API instance loss | 0 (stateless process) | 0 |
| Loss of an in-memory draft/blocked brief | n/a today (D-007) | not applicable — never published |
| PostgreSQL primary loss (once D-007 binds persistence) | 15 min | last committed published version |
| EvidenceCorpus snapshot loss | 30 min | the pinned snapshot of each published brief |

## Backup and restore

1. Migration `0502_decision_brief` reserves `decision_brief_brief`, `_section`,
   `_cited_statement`, `_citation`, `_rejected_proposal`; the SQLAlchemy adapter is part of D-007.
   Until then the repository is in-memory and a restart discards drafts — published artefacts do not
   survive a restart yet. This is recorded, not hidden.
2. When the adapter lands: back the five tables up with the normal PostgreSQL backup, restore into a
   clean database, run `alembic upgrade head`, then verify:
   - `SELECT count(*) FROM decision_brief_brief` matches the expected published versions;
   - no row has `status = 'published'` with a missing section (eight per brief);
   - every `_citation` row references a resolvable `passage_id`.
3. The corpus is the citation source of truth: restoring the brief without the pinned corpus
   snapshot produces an artefact whose citations cannot be opened. Restore both, snapshot first.

## Failover

The process is stateless apart from the repository. Multiple replicas can serve reads. Publication
is a transaction: run → consensus → provenance gate → assemble → resolve citations → freeze → save
and publish events in one unit of work, so a failover mid-publication leaves no half-frozen version.

After failover:

1. `GET /readyz` — `decision_brief` field (`ok`/`degraded`) and `decision_brief_gates`.
2. Publish a successor (`POST /briefs/{id}:version`) only when the prior version is retrievable.
3. Compare the regenerated artefact with the stored one (`ReproductionCheck`); a mismatch is a
   defect, not a data-repair task.

## Integrity checks

- **Immutability**: a published version cannot be changed — attribute writes and every section-map
  mutator raise `PUBLISHED_BRIEF_IMMUTABLE`.
- **Completeness**: exactly the eight `SectionKind` values, at their frozen ordinals.
- **Evidence**: no `evidenced` statement without at least one citation; claim ids never substitute.
- **Citations**: every citation resolves at publication time; unresolved ones block and are audited.
- **Disclosure**: each rejected proposal of the run is disclosed, and the disclaimer carries the
  model/prompt reference.
- **Honesty**: a vetoed topic is stated `blocked` with its blockers, never as a recommendation.
- **Lineage**: version N+1 references N and states a reason; N is unchanged and retrievable.
- **No skipped gate**: an unwired publication port returns `BRIEF_GATE_UNAVAILABLE`, it never
  publishes.
