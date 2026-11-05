# Runbook — EvidenceCorpus

Module-specific operations for the evidence corpus. Platform procedures live in
[`runbook.md`](runbook.md); this file is the module view a corpus operator needs.

## Startup sequence

1. PostgreSQL 16 with `pgvector` and `pg_trgm` is reachable (`docker compose up -d db`).
2. `uv run alembic upgrade head` — the corpus search index needs revision
   `0102_evidence_corpus_index` (`evidence_corpus_indexed_passage`, `evidence_corpus_index_manifest`).
3. Start the API (`uv run hps-api`); `/readyz` must report `{"checks": {"database": "ok"}}`.
4. Ingest one document and verify `GET /api/v1/passages/{id}` resolves a citation before a demo.

## Ingestion pipeline and where it can stop

```
POST /corpus/documents
  → content hash (idempotent re-ingest)
  → probe page facts           → OCR when no text layer / glyph damage
  → extract text + quality     → quarantine when confidence < 0.85 or glyph damage > 0.15
  → segment articles           → single article or clipping digest (`---` separators)
  → classify authority         → refused for source_type=unknown
  → index citable passages     → tsvector rows + manifest version
  → pin snapshot               → document ids + index version hashed together
```

| Failure | Code | Operator action |
|---|---|---|
| Unreadable/encrypted PDF, missing OCR stack | `EXTRACTION_FAILED` (422) | check the file; install Tesseract for scans |
| Low-fidelity scan | `DocumentQuarantined` event, `citable: false` | re-scan at higher DPI; do not lower the threshold |
| Segmentation before extraction | `DOCUMENT_NOT_CITABLE` (409) | extract first |
| Undeclared source type | `SOURCE_TYPE_UNKNOWN` (422) | re-ingest with `source_type` |
| Re-extraction attempt | `ALREADY_EXTRACTED` (409) | re-ingest the file; extraction is assigned once |
| Re-classification attempt | `AUTHORITY_ALREADY_ASSIGNED` (409) | authority is frozen at ingestion |
| Unknown run/snapshot/passage/article/document | `*_NOT_FOUND` (404) | use ids returned by the create endpoints |

## Person-level output

`SpeakerKind.PERSON` and `ANONYMOUS` passages are created non-citable and never reach
`publishable_passages()`; `PersonalQuotationExcluded` records the span. If a person-attributed
statement appears in an evidence pack, the bug is upstream of retrieval — check the segmentation
event log for the passage id.

## Citation verification

`GET /api/v1/passages/{id}` returns `outlet`, `published_on`, `page_from/page_to`, `offsets` and
`source_uri`. Verification = open the source at that page and compare `source_text[start:end]` with
the returned `text`. If they differ, the passage was re-segmented without re-indexing: re-run
`IndexIngestedPassages` for that document.

## Index recovery

1. `select index_version, is_current from evidence_corpus_index_manifest;` — exactly one row is
   current.
2. Re-index per document (idempotent): the writer truncates the document's rows before inserting.
3. German search smoke test:
   `select passage_id from evidence_corpus_indexed_passage where tsv @@ plainto_tsquery('german', 'Kassenstellen');`
4. If the manifest has no current row, re-index any document to publish a version, then re-pin the
   snapshot used by the demo.

## Snapshots and reproducibility

A snapshot pins document ids plus the index version. Re-ingestion never changes what an old
snapshot resolves to; only a new snapshot does. Before a demo: pin a labelled snapshot and quote its
`manifest_hash` in the brief.

## Observability

| Signal | Where |
|---|---|
| Request log with `trace_id`, method, path, status, duration | stdout JSON |
| Domain events (`domain_event`, `event_name`) | stdout JSON |
| Counters (`http_requests_total`, `http_request_duration_ms_total`, `domain_events_total`) | `GET /metrics` |
| Liveness / readiness | `GET /healthz`, `GET /readyz` |
| Search index state | `evidence_corpus_index_manifest.is_current` |

## Contract drift

`python3 .pi/scripts/ci/check_evidence_corpus_contract.py` proves the route inventory, enum
vocabulary, authority rubric, event payloads, error codes, port implementations and aggregate
invariants. It runs in CI (architecture job) and in the hardening stage runner.
