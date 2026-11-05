"""Frozen entities and aggregates of the EvidenceCorpus bounded context.

Canonical: .pi/architecture/modules/evidence-corpus.md

CONTRACT FREEZE — field sets, aggregate boundaries and method signatures are frozen; behaviour is a
stub raising ``NotImplementedError`` until the owning implementation issue lands. Aggregate
boundaries are deliberately visible here: `Document` is per source file, `IngestionRun` records
outcomes without containing documents, snapshots are manifests.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from enum import StrEnum

from evidence_corpus.domain.events import DomainEvent
from evidence_corpus.domain.values import (
    ArticleSection,
    AuthorityTier,
    ExtractionQuality,
    LanguageTag,
    Offsets,
    Provenance,
    QuotationBlock,
    SourceType,
    SpeakerKind,
)


@dataclass(frozen=True, slots=True)
class Publication:
    """The outlet issue/edition a Document was published in."""

    outlet: str
    published_on: date
    medium: str


@dataclass(slots=True)
class Passage:
    """Smallest citable text span; the unit indexed, retrieved and cited.

    Identity is ``id``; the span is fully described by ``offsets`` inside the parent Article,
    ``speaker_kind`` and ``section`` so a citation never depends on string search.
    """

    id: str
    article_id: str
    document_id: str
    ord: int
    text: str
    offsets: Offsets
    speaker_kind: SpeakerKind
    citable: bool
    section: ArticleSection = ArticleSection.BODY
    provenance: Provenance | None = None


@dataclass(slots=True)
class Article:
    """Editorial unit segmented out of a Document, with headline, date and page range."""

    id: str
    document_id: str
    headline: str
    body: str
    page_from: int
    page_to: int
    language: LanguageTag
    is_canonical: bool = True
    passages: list[Passage] = field(default_factory=list)
    quotation_blocks: list[QuotationBlock] = field(default_factory=list)
    events: list[DomainEvent] = field(default_factory=list)

    def publishable_passages(self) -> list[Passage]:
        """Return only citable passages (invariant 5 enforced at this boundary).

        TODO(document-aggregate): implemented by the passage/speaker implementation issues.
        """
        raise NotImplementedError("Article.publishable_passages is a frozen stub")

    def passage_count(self) -> int:
        """Number of passages, used by the `ArticleSegmented` payload.

        TODO(document-aggregate): implemented with the aggregate behaviour.
        """
        raise NotImplementedError("Article.passage_count is a frozen stub")


@dataclass(frozen=True, slots=True)
class IndexManifest:
    """Published index state a snapshot searches; part of the reproducibility contract."""

    index_version: str
    embedding_model: str
    searchable_since: datetime
    passage_count: int


@dataclass(slots=True)
class CorpusSnapshot:
    """Manifest of the documents and index version a run may search (own transaction)."""

    id: str
    label: str
    manifest_hash: str
    pinned_at: datetime
    document_ids: list[str]
    index_manifest: IndexManifest


class RunStatus(StrEnum):
    """Lifecycle of an IngestionRun."""

    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class IngestionOutcome(StrEnum):
    """Per-document outcome recorded by an IngestionRun."""

    ACCEPTED = "accepted"
    QUARANTINED = "quarantined"
    FAILED = "failed"


@dataclass(slots=True)
class IngestionRun:
    """One auditable batch execution: outcome counts and retry lineage."""

    id: str
    shard_label: str
    status: RunStatus = RunStatus.RUNNING
    attempted: int = 0
    accepted: int = 0
    quarantined: int = 0
    failed: int = 0
    events: list[DomainEvent] = field(default_factory=list)

    def record(self, outcome: IngestionOutcome) -> None:
        """Record one document outcome; illegal after the run is closed.

        TODO(ingestion-run): implemented with the IngestionRun aggregate issue.
        """
        raise NotImplementedError("IngestionRun.record is a frozen stub")

    def complete(self) -> None:
        """Close the run once and emit `IngestionRunCompleted`.

        TODO(ingestion-run): implemented with the IngestionRun aggregate issue.
        """
        raise NotImplementedError("IngestionRun.complete is a frozen stub")


@dataclass(slots=True)
class Document:
    """Aggregate root: a physical source file with extraction state and citable passages.

    Invariants (enforced by behaviour, never by setters):
    1. a Passage always has a resolvable parent Article and Document with a source URI;
    2. tier and quality are assigned once and immutable thereafter;
    3. passage offsets stay inside the parent Article and never overlap siblings;
    4. below-threshold extraction produces no citable passages;
    5. person-attributed quotations never become citable;
    6. authority is evaluated per claim type;
    7. the source type is explicit and `unknown` cannot be promoted.
    """

    id: str
    source_uri: str
    content_hash: str
    publication: Publication
    source_type: SourceType
    language: LanguageTag
    tier: AuthorityTier | None = None
    quality: ExtractionQuality | None = None
    extracted_text: str | None = None
    articles: list[Article] = field(default_factory=list)
    events: list[DomainEvent] = field(default_factory=list)

    def record_extraction(self, text: str, quality: ExtractionQuality) -> None:
        """Assign the single extraction outcome, quarantining the document if quality fails.

        A second call raises :class:`AlreadyExtracted`; tier and quality stay unchanged.
        TODO(document-record-extraction): implemented by ISSUE document-record-extraction.
        """
        raise NotImplementedError("Document.record_extraction is a frozen stub")

    def add_article(self, headline: str, body: str, page_from: int, page_to: int) -> Article:
        """Segment one Article; refused when the document is not citable.

        TODO(segmentarticle): implemented by ISSUE segmentarticle.
        """
        raise NotImplementedError("Document.add_article is a frozen stub")

    def classify(self, tier: AuthorityTier) -> None:
        """Assign authority once and freeze it (invariant 2/6).

        TODO(classifysourceauthority): implemented by ISSUE classifysourceauthority.
        """
        raise NotImplementedError("Document.classify is a frozen stub")

    def is_citable(self) -> bool:
        """Whether this document may produce citable passages (invariant 4).

        TODO(document-record-extraction): implemented with the quality gate.
        """
        raise NotImplementedError("Document.is_citable is a frozen stub")

    def publishable_passages(self) -> list[Passage]:
        """Only citable passages leave the aggregate.

        TODO(document-aggregate): implemented with the aggregate behaviour.
        """
        raise NotImplementedError("Document.publishable_passages is a frozen stub")

    def drain_events(self) -> list[DomainEvent]:
        """Return and clear pending events for the outbox writer.

        TODO(document-aggregate): implemented with the aggregate behaviour.
        """
        raise NotImplementedError("Document.drain_events is a frozen stub")
