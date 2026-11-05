---
guardian_issue:
  id: "ISSUE-CONTRACT-FREEZE"
  epic: "evidence-corpus"
  component: "Contract Freeze"
  module: "evidence-corpus"
  status: planned
  priority: critical
  dependencies: []

  in_scope:
    - Define public interfaces for all components in this epic
    - Define DTOs, schemas, and API contracts
    - Document event payloads and topics
    - Create interface stubs with no implementation
    - Freeze: no implementation changes without contract change

  out_of_scope:
    - Any implementation logic
    - Database schema changes
    - Infrastructure setup

  affected_layers:
    domain:
      - Interface definitions for domain services
    application:
      - Input/output DTO definitions
    api:
      - REST/event contracts

  canonical_references:
    - module: ".pi/architecture/modules/evidence-corpus.md"

  acceptance_criteria:
    - "All component interfaces defined as stubs (TODO bodies)"
    - "DTO schemas documented with field names and types"
    - "API contracts frozen and reviewed"
    - "Implementation PRs reference these contracts"

  validators:
    - architecture
    - canonical

  implementation_notes: |
    Define the contract before any implementation. Every implementation issue
    depends on this contract being frozen first. The contract should include:
    interfaces, types, DTOs, event schemas, API paths, error formats.

  file_changes:
    - "create: src/evidence-corpus/domain/"
    - "create: src/evidence-corpus/application/"
    - "create: src/evidence-corpus/infrastructure/"
    - "create: src/evidence-corpus/interfaces/"
---

# Contract Freeze: evidence-corpus

## Intent

Define and freeze all public interfaces, contracts, and schemas for the evidence-corpus
epic before any implementation begins. This prevents architecture drift — implementation
must satisfy contracts, not the other way around.

## Included Components

- Entities
- Value Objects (entity-vs-VO justification)
- Service classification
- `Document.record_extraction`
- Extraction quality gate
- `Passage.offsets`
- `SpeakerKind` classification
- `ExtractDocumentText`
- `SegmentArticle`
- Provenance resolution
- `ClassifySourceAuthority`
- `LinkCanonicalArticle`
- `PinCorpusSnapshot`
- `IndexIngestedPassages`
- API contract

## What Must Be Frozen

### Interfaces
- Service interfaces for every component
- Repository/DAO interfaces
- Factory interfaces

### Contracts
- Input/output DTO schemas
- API endpoint contracts (method, path, request/response)
- Event payload schemas
- Error response formats

### Out of Bounds (no contracts needed)
- Internal implementation details
- Database column names (hidden behind repository)
- Framework-specific annotations

## Acceptance Criteria

| # | Criterion | How to Verify |
|---|-----------|---------------|
| 1 | All component interfaces defined as stubs (TODO bodies) | Check src/<module>/domain/ and application/ |
| 2 | Contracts reviewed and frozen | PR approval |
| 3 | DTO schemas documented with field names and types | OpenAPI / record types |
| 4 | Implementation depends on contracts | No implementation without interface |

## Full Module Acceptance Criteria (for reference)

> These are the complete ACs for the module. The contract freeze must define the interfaces
> so every row below can be implemented in subsequent issues.

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

## Full Implementation Sequence (for reference)

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

> **Agent:** Create interface-only files. No implementation. Use Clean Architecture layers:
> 1. Read the architecture module to understand each component's role
> 2. Place domain interfaces in domain/, service interfaces in application/, DTOs in application/
> 3. Controllers/routers are CONCRETE — they do NOT get interfaces. The concrete router/handler class goes directly in interfaces/http/ without a separate contract file.
> 4. Event schemas go in domain/event/
> 5. Repository interfaces go in infrastructure/repository/
>
> The goal is a reviewed, frozen contract that implementation issues can depend on.
