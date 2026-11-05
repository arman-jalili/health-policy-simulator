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

from evidence_corpus.domain.errors import (
    AlreadyExtracted,
    AuthorityAlreadyAssigned,
    DocumentNotCitable,
    OffsetsOutOfBounds,
    OverlappingPassages,
    PassageNotFound,
    RunAlreadyClosed,
    SourceTypeUnknown,
)
from evidence_corpus.domain.events import (
    ArticleSegmented,
    AuthorityTierAssigned,
    DocumentIngested,
    DocumentQuarantined,
    DomainEvent,
    IngestionRunCompleted,
    InstitutionalStatementAttributed,
    PassageRevertedFromIndex,
    PersonalQuotationExcluded,
    QuotationBlockDetected,
)
from evidence_corpus.domain.values import (
    CITABLE_SPEAKER_KINDS,
    DEFAULT_MINIMUM_CONFIDENCE,
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
from shared.ids import new_id


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

    @classmethod
    def new(
        cls,
        *,
        article_id: str,
        document_id: str,
        ord: int,
        text: str,
        offsets: Offsets,
        speaker_kind: SpeakerKind,
        section: ArticleSection = ArticleSection.BODY,
        provenance: Provenance | None = None,
    ) -> Passage:
        """Create a passage; citability is derived from attribution, never from the caller."""
        return cls(
            id=new_id("psg"),
            article_id=article_id,
            document_id=document_id,
            ord=ord,
            text=text,
            offsets=offsets,
            speaker_kind=speaker_kind,
            citable=speaker_kind in CITABLE_SPEAKER_KINDS,
            section=section,
            provenance=provenance,
        )


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

    def add_passage(
        self,
        *,
        text: str,
        offsets: Offsets,
        speaker_kind: SpeakerKind,
        section: ArticleSection = ArticleSection.BODY,
        provenance: Provenance | None = None,
    ) -> Passage:
        """Add a passage inside this article's body (invariants 3 and 5).

        Offsets must lie within ``body`` and must not overlap an existing sibling. Citability is
        derived from attribution: person- and anonymous-attributed quotations never become citable
        and the exclusion is recorded as an event.
        """
        self._assert_offsets_within(offsets)
        for sibling in self.passages:
            if sibling.offsets.overlaps(offsets):
                raise OverlappingPassages(article_id=self.id, first=sibling.id, second="<new>")

        passage = Passage.new(
            article_id=self.id,
            document_id=self.document_id,
            ord=len(self.passages),
            text=text,
            offsets=offsets,
            speaker_kind=speaker_kind,
            section=section,
            provenance=provenance,
        )
        self.passages.append(passage)
        self._record_attribution(passage)
        return passage

    def quarantine_passage(self, passage_id: str, reason: str) -> None:
        """Withdraw a passage from citation without deleting it (audit keeps the row)."""
        for passage in self.passages:
            if passage.id == passage_id:
                passage.citable = False
                self.events.append(PassageRevertedFromIndex(passage_id=passage_id, reason=reason))
                return
        raise PassageNotFound(passage_id)

    def publishable_passages(self) -> list[Passage]:
        """Only citable passages leave this article (invariant 5)."""
        return [passage for passage in self.passages if passage.citable]

    def passage_count(self) -> int:
        """Number of passages, used by the `ArticleSegmented` payload."""
        return len(self.passages)

    def _assert_offsets_within(self, offsets: Offsets) -> None:
        article_length = len(self.body)
        if offsets.end > article_length or offsets.start < 0:
            raise OffsetsOutOfBounds(
                article_id=self.id,
                start=offsets.start,
                end=offsets.end,
                article_length=article_length,
            )

    def _record_attribution(self, passage: Passage) -> None:
        if passage.section is ArticleSection.QUOTATION:
            self.events.append(
                QuotationBlockDetected(passage_id=passage.id, speaker_kind=passage.speaker_kind)
            )
        if passage.speaker_kind is SpeakerKind.INSTITUTION:
            self.events.append(
                InstitutionalStatementAttributed(
                    passage_id=passage.id,
                    institution_identity=passage.text.split(":")[0][:120],
                )
            )
        else:
            self.events.append(
                PersonalQuotationExcluded(
                    passage_id=passage.id,
                    span=(passage.offsets.start, passage.offsets.end),
                )
            )


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

    @classmethod
    def pin(
        cls,
        *,
        label: str,
        document_ids: list[str],
        index_manifest: IndexManifest,
        pinned_at: datetime,
        manifest_hash: str,
    ) -> CorpusSnapshot:
        """Create the immutable manifest for one pinned corpus state."""
        return cls(
            id=new_id("snp"),
            label=label,
            manifest_hash=manifest_hash,
            pinned_at=pinned_at,
            document_ids=sorted(set(document_ids)),
            index_manifest=index_manifest,
        )


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
    failure_reason: str | None = None
    events: list[DomainEvent] = field(default_factory=list)

    def record(self, outcome: IngestionOutcome) -> None:
        """Record one document outcome; illegal after the run is closed."""
        if self.status is not RunStatus.RUNNING:
            raise RunAlreadyClosed(self.id)

        self.attempted += 1
        if outcome is IngestionOutcome.ACCEPTED:
            self.accepted += 1
        elif outcome is IngestionOutcome.QUARANTINED:
            self.quarantined += 1
        else:
            self.failed += 1

    def complete(self) -> None:
        """Close the run once and emit `IngestionRunCompleted`."""
        if self.status is not RunStatus.RUNNING:
            raise RunAlreadyClosed(self.id)

        self.status = RunStatus.COMPLETED
        self.events.append(
            IngestionRunCompleted(
                run_id=self.id,
                attempted=self.attempted,
                accepted=self.accepted,
                quarantined=self.quarantined,
                failed=self.failed,
            )
        )

    def fail(self, reason: str) -> None:
        """Close the run as failed, keeping the counts reached so far."""
        if self.status is not RunStatus.RUNNING:
            raise RunAlreadyClosed(self.id)
        self.status = RunStatus.FAILED
        self.failure_reason = reason


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

    @classmethod
    def register(
        cls,
        *,
        source_uri: str,
        content_hash: str,
        publication: Publication,
        source_type: SourceType,
        language: LanguageTag,
    ) -> Document:
        """Factory for a newly ingested source file (no extraction yet)."""
        return cls(
            id=new_id("doc"),
            source_uri=source_uri,
            content_hash=content_hash,
            publication=publication,
            source_type=source_type,
            language=language,
        )

    def record_extraction(self, text: str, quality: ExtractionQuality) -> None:
        """Assign the single extraction outcome, quarantining the document if quality fails.

        Invariant 2: a second call raises :class:`AlreadyExtracted`; tier and quality stay
        unchanged.
        Invariant 4: below-threshold extraction is recorded as quarantine, not as failure.
        """
        if self.quality is not None:
            raise AlreadyExtracted(self.id)

        self.extracted_text = text
        self.quality = quality
        if not quality.is_acceptable():
            self.events.append(
                DocumentQuarantined(
                    document_id=self.id,
                    quality=quality,
                    threshold=DEFAULT_MINIMUM_CONFIDENCE,
                )
            )
            return

        self.events.append(
            DocumentIngested(
                document_id=self.id,
                source_uri=self.source_uri,
                content_hash=self.content_hash,
                quality_method=quality.method,
            )
        )

    def add_article(self, headline: str, body: str, page_from: int, page_to: int) -> Article:
        """Segment one Article; refused when the document is not citable (invariant 4)."""
        if not self.is_citable():
            raise DocumentNotCitable(self.id)
        if not headline.strip() or not body.strip():
            raise ValueError("article headline and body must not be empty")
        if page_from < 1 or page_to < page_from:
            raise ValueError("page range must be 1-based and ordered")

        article = Article(
            id=new_id("art"),
            document_id=self.id,
            headline=headline.strip(),
            body=body,
            page_from=page_from,
            page_to=page_to,
            language=self.language,
        )
        self.articles.append(article)
        self.events.append(
            ArticleSegmented(
                document_id=self.id,
                article_id=article.id,
                passage_count=article.passage_count(),
            )
        )
        return article

    def classify(self, tier: AuthorityTier) -> None:
        """Assign authority once and freeze it (invariants 2 and 7).

        An unclassified source type can never be promoted: the operator must declare it first.
        """
        if self.tier is not None:
            raise AuthorityAlreadyAssigned(self.id)
        if self.source_type is SourceType.UNKNOWN:
            raise SourceTypeUnknown(self.id)

        self.tier = tier
        self.events.append(AuthorityTierAssigned(document_id=self.id, tier=tier))

    def is_citable(self) -> bool:
        """Whether this document may produce citable passages (invariants 4 and 7)."""
        return (
            self.quality is not None
            and self.quality.is_acceptable()
            and self.source_type is not SourceType.UNKNOWN
        )

    def publishable_passages(self) -> list[Passage]:
        """Only citable passages leave the aggregate."""
        return [passage for article in self.articles for passage in article.publishable_passages()]

    def drain_events(self) -> list[DomainEvent]:
        """Return and clear pending events for the outbox writer."""
        events = list(self.events)
        self.events.clear()
        return events
