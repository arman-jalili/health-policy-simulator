---
guardian_issue:
  id: "ISSUE-EVIDENCE-CORPUS-3"
  epic: "TBD"
  component: "Service classification"
  module: "evidence-corpus"
  status: planned
  priority: high
  dependencies:
    - "none"

  in_scope:
    - "A second call on the same Document raises `AlreadyExtracted`; tier and quality are unchanged after reclassification attempt"
    - "A document with confidence below threshold yields `DocumentQuarantined` and `publishable_passages()` returns `[]`"
    - "Constructing offsets outside the parent article bounds raises; over-investigation guard: overlapping siblings rejected"

  out_of_scope:
    - Changes to upstream components (none)
    - UI/frontend changes
    - Deployment pipeline configuration

  canonical_references:
    - module: ".pi/architecture/modules/evidence-corpus.md"
    - acceptance_criteria: ".pi/architecture/modules/evidence-corpus.md#acceptance-criteria"

  acceptance_criteria:
    - "A second call on the same Document raises `AlreadyExtracted`; tier and quality are unchanged after reclassification attempt"
    - "A document with confidence below threshold yields `DocumentQuarantined` and `publishable_passages()` returns `[]`"
    - "Constructing offsets outside the parent article bounds raises; over-investigation guard: overlapping siblings rejected"

  validators:
    - ci
    - tests
    - security
    - architecture
    - canonical

  implementation_notes: |
    Read .pi/architecture/modules/evidence-corpus.md BEFORE implementing.
    All Acceptance Criteria in that file must be satisfied before this issue is closed.
    Component focus: Service classification.
    CONCRETE IMPLEMENTATIONS MUST BE CREATED — interface stubs from the contract freeze
    are not sufficient. Each domain service/aggregate needs a concrete .impl.py file.

  file_changes:
    - "create: src/evidence-corpus/domain/"
    - "create: src/evidence-corpus/application/"
    - "create: src/evidence-corpus/infrastructure/"
    - "modify: src/evidence-corpus/interfaces/"
    -     - "update: tests/ (failing tests already generated — make them pass)"
---

# ISSUE-EVIDENCE-CORPUS-3: Implement Service classification — evidence-corpus

## Intent

Implement **Service classification** for the `evidence-corpus` module.

> ⚠️ **Read before implementing:** `.pi/architecture/modules/evidence-corpus.md`
> Every item in the **Acceptance Criteria** section of that file must be satisfied
> before this issue is closed — including adapter, mapper, and WireMock items.

## Architecture Context

- **Module:** evidence-corpus
- **Component:** Service classification
- **Status:** planned
- **Dependencies:** none

## In Scope (this component)

- A second call on the same Document raises `AlreadyExtracted`; tier and quality are unchanged after reclassification attempt
- A document with confidence below threshold yields `DocumentQuarantined` and `publishable_passages()` returns `[]`
- Constructing offsets outside the parent article bounds raises; over-investigation guard: overlapping siblings rejected

## Acceptance Criteria (this issue)

These acceptance criteria must be satisfied before this issue can be closed:

| # | Criterion | Verify In |
|---|-----------|-----------|
| 1 | A second call on the same Document raises `AlreadyExtracted`; tier and quality are unchanged after reclassification attempt | `tests/domain/test_document.py` |
| 2 | A document with confidence below threshold yields `DocumentQuarantined` and `publishable_passages()` returns `[]` | unit |
| 3 | Constructing offsets outside the parent article bounds raises; over-investigation guard: overlapping siblings rejected | unit |

## Full Module Acceptance Criteria

> All items below must pass before the **epic** is closed.
> Items may be split across multiple issues — verify your component's items before creating the MR.

| # | Component | Criterion | Verify In |
|---|-----------|-----------|-----------|
| 1 | `Document.record_extraction` | A second call on the same Document raises `AlreadyExtracted`; tier and quality are unchanged after reclassification attempt | `tests/domain/test_document.py` |
| 2 | Extraction quality gate | A document with confidence below threshold yields `DocumentQuarantined` and `publishable_passages()` returns `[]` | unit |
| 3 | `Passage.offsets` | Constructing offsets outside the parent article bounds raises; over-investigation guard: overlapping siblings rejected | unit |
| 4 | `SpeakerKind` classification | A person-attributed quotation produces `PersonalQuotationExcluded` and never reaches `publishable_passages()`; an institution-attributed statement remains citable | unit + integration |
| 5 | `ExtractDocumentText` | A scanned PDF without text layer routes to OCR and yields non-empty text with `quality.method == "ocr"` | integration |
| 6 | `SegmentArticle` | A 3-clipping digest yields exactly 3 articles with distinct headlines and page ranges | integration |
| 7 | Provenance resolution | `GET /api/v1/passages/{id}` returns outlet, date, page and offsets that reproduce the exact text slice from the source file | integration |
| 8 | `ClassifySourceAuthority` | Unknown source type is refused (`SourceTypeUnknown`); a press report never outranks a statute for a legal claim type | unit |
| 9 | `LinkCanonicalArticle` | Two identical texts link to one canonical article; citation counts do not double | integration |
| 10 | `PinCorpusSnapshot` | Snapshot pins documents + index version; re-running ingestion afterwards does not change passages visible through the old snapshot | integration |
| 11 | `IndexIngestedPassages` | Passages are searchable via `tsvector` within the same application run; re-indexing is idempotent | integration |
| 12 | API contract | All endpoints appear in generated OpenAPI and return the documented envelope; error paths use `{code,message,details,trace_id}` | contract test |

## Implementation Sequence (from module doc)

- 1. `Passage`, `Offsets`, `Provenance`, `AuthorityTier`, `SpeakerKind`, `LanguageTag` value objects + tests
- 2. `ExtractionQuality` gate + `Document.record_extraction` invariant tests
- 3. `Document` aggregate with article segmentation and citability spec
- 4. `ExtractionPort` with native extractor (PyMuPDF) → integration test on 5 real PDFs
- 5. OCR fallback adapter + quality comparison metric
- 6. `ArticleBoundaryStrategy` variants (single article, clipping digest)
- 7. `Passage` chunking with offsets + speaker classification (person vs institution)
- 8. `ClassifySourceAuthority` + canonical-article linking (content hash + similarity)
- 9. `IndexIngestedPassages`: `tsvector` writer + `passage_embedding` upserts
- 10. `PinCorpusSnapshot` manifest + `IndexManifest` publication
- 11. REST routers + OpenAPI contract tests

## Implementation

> **Agent instructions:**
> 1. Open `.pi/architecture/modules/evidence-corpus.md` — read the full Acceptance Criteria table
> 2. Identify which rows are your responsibility for **Service classification**
> 3. Create concrete implementation files (`.impl.py`) in `src/evidence-corpus/` — the interface stubs from the contract freeze are NOT enough
> 4. Each domain aggregate/service must have a working implementation with business logic
> 5. Verify each AC row is satisfied in `src/` before marking done
> 6. Run validators and create MR

### Steps

1. Read canonical architecture references
2. Run the pre-generated failing tests: `cd tests && pytest`
3. Verify tests FAIL (Red phase)
4. Implement domain entities and interfaces
5. Implement application service/handler
6. Add infrastructure connections
7. Run tests again — they should PASS (Green phase)
8. Refactor if needed (Refactor phase)
9. Write integration tests
10. Run all validators
11. Create MR
