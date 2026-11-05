# DR plan — EvidenceCorpus

Module-scoped recovery for the corpus. Platform-level targets and procedures live in
[`dr-plan.md`](dr-plan.md); this file covers what is specific to evidence.

## What is durable, what is derived

| Artefact | Durable? | Rebuildable from |
|---|---|---|
| Source files (`source_uri`) | yes — object storage, addressed by content hash | the archive itself |
| Documents, articles, passages | in-memory in the prototype (lost on restart) | re-ingestion of the source files |
| Search index (`evidence_corpus_indexed_passage`) | yes — PostgreSQL | re-indexing the documents |
| Index manifest versions | yes — PostgreSQL | re-indexing (version = hash of passage ids) |
| Snapshots (document ids + index version) | yes — PostgreSQL | re-pinning after re-ingestion |
| Domain events | outbox in production; logged now | event log in stdout |

Because passages are derived, the recovery unit is the **source file**, not the passage row. This is
why a re-extraction never destroys the original.

## Targets

| Scenario | RTO | RPO | Basis |
|---|---|---|---|
| Process restart | 2 min | 0 (sources durable) | re-ingest affected documents |
| Corpus database loss | 30 min | ≤ 15 min | restore PostgreSQL, re-index |
| Corrupted index / wrong model version | 15 min | 0 | re-index all documents, publish new manifest |
| Sybil/duplicate inflation discovered | manual | — | re-run canonical linking, re-pin snapshot |

## Recovery procedure — corpus database lost

1. Restore PostgreSQL from the latest base backup (platform DR plan).
2. `uv run alembic upgrade head` — corpus index revision must be present.
3. Re-ingest the demo document set from the source archive. Re-ingestion is idempotent per content
   hash, so repeated runs are safe.
4. Re-index: `IndexIngestedPassages` per document; confirm one `is_current` manifest row.
5. Re-pin the snapshot and record its `manifest_hash`; update the demo script.
6. Verify a citation end to end: `GET /api/v1/passages/{id}` reproduces the source slice.

## Recovery procedure — index corruption or stale passages

1. Stop writes (pause ingestion) so the manifest stops moving.
2. Re-index every affected document; the writer deletes a document's rows before inserting.
3. Publish a new manifest; old snapshots keep resolving to the old index version and remain
   reproducible — do not delete the old manifest rows.
4. Run the German search smoke test and one citation verification.

## Recovery procedure — bad authority classification

Authority is frozen at ingestion by design. Recovery is a new document version, never an in-place
edit:

1. Re-ingest the source with the correct `source_type`.
2. Re-run classification and canonical linking.
3. Re-index and pin a new snapshot; retire the old snapshot from the demo script.

## Integrity checks after recovery

```sql
select count(*) from evidence_corpus_indexed_passage;
select index_version from evidence_corpus_index_manifest where is_current;
select passage_id from evidence_corpus_indexed_passage
  where tsv @@ plainto_tsquery('german', 'Kassenstellen') limit 5;
```

- `is_current` must select exactly one row.
- Indexed passage count must match the publishable passages of the pinned snapshot.
- Zero indexed passages for a document that reports `citable = true` means indexing was skipped.

## Communication

Single operator for the prototype: record the incident (timeline, cause, achieved RTO/RPO, snapshot
hash after recovery) in `.pi/workpad.md` and tell the demo owner before re-running the negotiation.
