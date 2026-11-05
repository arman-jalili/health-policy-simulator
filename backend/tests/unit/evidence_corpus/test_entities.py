"""Entity and aggregate contract: structure plus the behaviour that enforces the invariants.

Aggregate boundaries are part of the contract: `Document` is per-file (not the corpus),
`IngestionRun` records outcomes and contains no documents, snapshots are manifests.
"""

from __future__ import annotations

import dataclasses
from datetime import UTC, date, datetime

import pytest

from evidence_corpus.domain.entities import (
    Article,
    CorpusSnapshot,
    Document,
    IndexManifest,
    IngestionOutcome,
    IngestionRun,
    Passage,
    Publication,
    RunStatus,
)
from evidence_corpus.domain.errors import (
    AlreadyExtracted,
    AuthorityAlreadyAssigned,
    DocumentNotCitable,
    OffsetsOutOfBounds,
    OverlappingPassages,
    RunAlreadyClosed,
    SourceTypeUnknown,
)
from evidence_corpus.domain.events import (
    ArticleSegmented,
    AuthorityTierAssigned,
    DocumentIngested,
    DocumentQuarantined,
    IngestionRunCompleted,
    InstitutionalStatementAttributed,
    PersonalQuotationExcluded,
    QuotationBlockDetected,
)
from evidence_corpus.domain.values import (
    ArticleSection,
    AuthorityTier,
    ExtractionMethod,
    ExtractionQuality,
    LanguageTag,
    Offsets,
    Provenance,
    SourceType,
    SpeakerKind,
)

from .contract_helpers import enum_values, field_names

GOOD_QUALITY = ExtractionQuality(ExtractionMethod.NATIVE, 0.95, 0.0)
POOR_QUALITY = ExtractionQuality(ExtractionMethod.OCR, 0.41, 0.55)


def _document(source_type: SourceType = SourceType.PRESS_REPORT) -> Document:
    return Document.register(
        source_uri="s3://corpus/std-2026-10-01.pdf",
        content_hash="sha256:abc",
        publication=Publication(
            outlet="Der Standard",
            published_on=date(2026, 10, 1),
            medium="print",
        ),
        source_type=source_type,
        language=LanguageTag("de-AT"),
    )


def _extracted_document() -> Document:
    document = _document()
    document.record_extraction("Erster Artikel.\fZweiter Artikel.", GOOD_QUALITY)
    return document


def _article() -> Article:
    document = _extracted_document()
    return document.add_article("Kassenstellen", "Die Kassenstellen werden aufgestockt.", 1, 1)


class TestPublication:
    def test_holds_outlet_date_and_medium(self) -> None:
        assert field_names(Publication) == ["outlet", "published_on", "medium"]

    def test_is_an_immutable_value(self) -> None:
        publication = Publication(
            outlet="Der Standard", published_on=date(2026, 10, 1), medium="print"
        )
        with pytest.raises(dataclasses.FrozenInstanceError):
            publication.outlet = "Kurier"  # type: ignore[misc]


class TestDocumentAggregate:
    def test_declares_the_identity_and_provenance_fields(self) -> None:
        names = field_names(Document)

        assert names[:6] == [
            "id",
            "source_uri",
            "content_hash",
            "publication",
            "source_type",
            "language",
        ]
        assert {"tier", "quality", "articles", "events"} <= set(names)

    def test_register_creates_an_unclassified_document(self) -> None:
        document = _document()

        assert document.id.startswith("doc_")
        assert document.tier is None
        assert document.quality is None
        assert document.articles == []
        assert document.events == []

    def test_mutation_goes_through_behaviour_not_setters(self) -> None:
        assert {name for name in dir(Document) if name.startswith("set_")} == set()
        assert {"record_extraction", "add_article", "classify", "is_citable"} <= set(dir(Document))

    def test_record_extraction_assigns_once(self) -> None:
        document = _document()

        document.record_extraction("Text", GOOD_QUALITY)

        assert document.quality is GOOD_QUALITY
        assert document.extracted_text == "Text"
        with pytest.raises(AlreadyExtracted):
            document.record_extraction("Anderer Text", GOOD_QUALITY)
        assert document.quality is GOOD_QUALITY
        assert document.extracted_text == "Text"

    def test_record_extraction_emits_exactly_one_outcome_event(self) -> None:
        document = _document()

        document.record_extraction("Text", GOOD_QUALITY)

        events = document.drain_events()
        assert len(events) == 1
        assert isinstance(events[0], DocumentIngested)
        assert events[0].quality_method is ExtractionMethod.NATIVE
        assert document.drain_events() == []

    def test_below_threshold_extraction_quarantines_as_an_event(self) -> None:
        document = _document()

        document.record_extraction("garbled", POOR_QUALITY)

        events = document.drain_events()
        assert isinstance(events[0], DocumentQuarantined)
        assert events[0].threshold > 0
        assert document.is_citable() is False

    def test_is_citable_requires_accepted_extraction(self) -> None:
        document = _document()

        assert document.is_citable() is False
        document.record_extraction("Text", GOOD_QUALITY)
        assert document.is_citable() is True

    def test_unknown_source_type_is_never_citable(self) -> None:
        document = _document(SourceType.UNKNOWN)
        document.record_extraction("Text", GOOD_QUALITY)

        assert document.is_citable() is False

    def test_add_article_refuses_a_non_citable_document(self) -> None:
        document = _document()

        with pytest.raises(DocumentNotCitable):
            document.add_article("headline", "body", 1, 1)

    def test_add_article_segments_and_emits(self) -> None:
        document = _extracted_document()
        document.drain_events()

        article = document.add_article(
            "Kassenstellen", "Die Kassenstellen werden aufgestockt.", 3, 3
        )

        assert article.id.startswith("art_")
        assert article.document_id == document.id
        assert article.headline == "Kassenstellen"
        events = document.drain_events()
        assert isinstance(events[0], ArticleSegmented)
        assert events[0].article_id == article.id
        assert events[0].passage_count == 0

    def test_add_article_rejects_empty_or_inverted_segments(self) -> None:
        document = _extracted_document()

        with pytest.raises(ValueError, match="headline"):
            document.add_article("  ", "body", 1, 1)
        with pytest.raises(ValueError, match="page range"):
            document.add_article("headline", "body", 2, 1)

    def test_classify_assigns_once_and_refuses_reclassification(self) -> None:
        document = _extracted_document()
        document.drain_events()

        document.classify(AuthorityTier.PRESS_REPORT)

        assert document.tier is AuthorityTier.PRESS_REPORT
        events = document.drain_events()
        assert isinstance(events[0], AuthorityTierAssigned)
        with pytest.raises(AuthorityAlreadyAssigned):
            document.classify(AuthorityTier.LEGISLATION)
        assert document.tier is AuthorityTier.PRESS_REPORT

    def test_classify_refuses_an_unknown_source_type(self) -> None:
        document = _document(SourceType.UNKNOWN)

        with pytest.raises(SourceTypeUnknown):
            document.classify(AuthorityTier.OTHER)
        assert document.tier is None

    def test_publishable_passages_flattens_citable_spans_only(self) -> None:
        document = _extracted_document()
        body = "Institution: wir zahlen. Person: ich auch."
        split = body.index("Person")
        article = document.add_article("headline", body, 1, 1)
        article.add_passage(
            text=body[:split].strip(),
            offsets=Offsets(0, split),
            speaker_kind=SpeakerKind.INSTITUTION,
        )
        article.add_passage(
            text=body[split:].strip(),
            offsets=Offsets(split, len(body)),
            speaker_kind=SpeakerKind.PERSON,
        )

        publishable = document.publishable_passages()

        assert len(publishable) == 1
        assert publishable[0].speaker_kind is SpeakerKind.INSTITUTION


class TestArticle:
    def test_is_the_editorial_unit_with_page_range(self) -> None:
        names = field_names(Article)

        assert names[:8] == [
            "id",
            "document_id",
            "headline",
            "body",
            "page_from",
            "page_to",
            "language",
            "is_canonical",
        ]
        assert {"passages", "quotation_blocks"} <= set(names)

    def test_add_passage_assigns_ordinals_and_citability(self) -> None:
        article = _article()
        article.events.clear()

        passage = article.add_passage(
            text="Die Kassenstellen werden",
            offsets=Offsets(0, 22),
            speaker_kind=SpeakerKind.INSTITUTION,
        )

        assert passage.id.startswith("psg_")
        assert passage.ord == 0
        assert passage.citable is True
        assert article.passage_count() == 1
        assert [type(event) for event in article.events] == [InstitutionalStatementAttributed]

    def test_person_attributed_quotations_are_non_citable_and_recorded(self) -> None:
        article = _article()
        article.events.clear()

        passage = article.add_passage(
            text="Die Kassenstellen werden",
            offsets=Offsets(0, 22),
            speaker_kind=SpeakerKind.PERSON,
            section=ArticleSection.QUOTATION,
        )

        assert passage.citable is False
        assert article.publishable_passages() == []
        assert [type(event) for event in article.events] == [
            QuotationBlockDetected,
            PersonalQuotationExcluded,
        ]

    def test_offsets_outside_the_body_are_refused(self) -> None:
        article = _article()

        with pytest.raises(OffsetsOutOfBounds):
            article.add_passage(
                text="beyond",
                offsets=Offsets(0, len(article.body) + 1),
                speaker_kind=SpeakerKind.INSTITUTION,
            )

    def test_overlapping_siblings_are_refused(self) -> None:
        article = _article()
        article.add_passage(
            text="Die Kassenstellen",
            offsets=Offsets(0, 17),
            speaker_kind=SpeakerKind.INSTITUTION,
        )

        with pytest.raises(OverlappingPassages):
            article.add_passage(
                text="stellen werden",
                offsets=Offsets(10, 24),
                speaker_kind=SpeakerKind.INSTITUTION,
            )

    def test_publishable_passages_returns_only_citable_spans(self) -> None:
        article = _article()

        assert article.publishable_passages() == []
        article.add_passage(
            text="Die Kassenstellen",
            offsets=Offsets(0, 17),
            speaker_kind=SpeakerKind.INSTITUTION,
        )
        assert len(article.publishable_passages()) == 1


class TestPassage:
    def test_is_the_smallest_citable_span(self) -> None:
        names = field_names(Passage)

        assert names[:8] == [
            "id",
            "article_id",
            "document_id",
            "ord",
            "text",
            "offsets",
            "speaker_kind",
            "citable",
        ]
        assert "section" in names

    def test_new_derives_citability_from_attribution(self) -> None:
        institutional = Passage.new(
            article_id="art_1",
            document_id="doc_1",
            ord=0,
            text="Institution: wir zahlen.",
            offsets=Offsets(0, 24),
            speaker_kind=SpeakerKind.INSTITUTION,
        )
        personal = Passage.new(
            article_id="art_1",
            document_id="doc_1",
            ord=1,
            text=" Person: ich auch.",
            offsets=Offsets(24, 43),
            speaker_kind=SpeakerKind.PERSON,
        )

        assert institutional.citable is True
        assert personal.citable is False

    def test_provenance_is_attached_for_citation_resolution(self) -> None:
        assert "provenance" in field_names(Passage)

        passage = Passage.new(
            article_id="art_1",
            document_id="doc_1",
            ord=0,
            text="Text",
            offsets=Offsets(0, 4),
            speaker_kind=SpeakerKind.INSTITUTION,
            provenance=Provenance(
                outlet="Der Standard",
                published_on=date(2026, 10, 1),
                medium="print",
                page_from=3,
                page_to=3,
                offsets=Offsets(0, 4),
                source_uri="s3://corpus/std-2026-10-01.pdf",
            ),
        )

        assert passage.provenance is not None
        assert passage.provenance.page_from == 3


class TestIngestionRun:
    def test_records_outcome_counts_and_owns_no_documents(self) -> None:
        names = field_names(IngestionRun)

        assert names[:3] == ["id", "shard_label", "status"]
        assert {"attempted", "accepted", "quarantined", "failed"} <= set(names)
        assert "documents" not in names

    def test_status_and_outcome_vocabularies_are_frozen(self) -> None:
        assert enum_values(RunStatus) == {"running", "completed", "failed"}
        assert enum_values(IngestionOutcome) == {"accepted", "quarantined", "failed"}

    def test_record_counts_each_outcome_once(self) -> None:
        run = IngestionRun(id="run_1", shard_label="shard-1")

        run.record(IngestionOutcome.ACCEPTED)
        run.record(IngestionOutcome.QUARANTINED)
        run.record(IngestionOutcome.FAILED)

        assert (run.attempted, run.accepted, run.quarantined, run.failed) == (3, 1, 1, 1)

    def test_complete_closes_once_and_emits_counts(self) -> None:
        run = IngestionRun(id="run_1", shard_label="shard-1")
        run.record(IngestionOutcome.ACCEPTED)

        run.complete()

        assert run.status is RunStatus.COMPLETED
        event = run.events[-1]
        assert isinstance(event, IngestionRunCompleted)
        assert event.accepted == 1
        with pytest.raises(RunAlreadyClosed):
            run.complete()

    def test_fail_marks_the_run_without_losing_counts(self) -> None:
        run = IngestionRun(id="run_1", shard_label="shard-1")
        run.record(IngestionOutcome.FAILED)

        run.fail("ocr backend unavailable")

        assert run.status is RunStatus.FAILED
        assert run.failure_reason == "ocr backend unavailable"
        with pytest.raises(RunAlreadyClosed):
            run.record(IngestionOutcome.ACCEPTED)


class TestSnapshotAndIndexManifest:
    def test_snapshot_is_a_manifest_not_a_corpus_root(self) -> None:
        assert field_names(CorpusSnapshot) == [
            "id",
            "label",
            "manifest_hash",
            "pinned_at",
            "document_ids",
            "index_manifest",
        ]

    def test_index_manifest_records_the_searchable_index_state(self) -> None:
        assert field_names(IndexManifest) == [
            "index_version",
            "embedding_model",
            "searchable_since",
            "passage_count",
        ]

    def test_pin_sorts_and_freezes_the_document_set(self) -> None:
        manifest = IndexManifest(
            index_version="idx-2026-11-05.1",
            embedding_model="text-embedding-3-small",
            searchable_since=datetime(2026, 11, 5, 9, 0, tzinfo=UTC),
            passage_count=120,
        )

        snapshot = CorpusSnapshot.pin(
            label="baseline",
            document_ids=["doc_b", "doc_a"],
            index_manifest=manifest,
            pinned_at=datetime(2026, 11, 5, 9, 5, tzinfo=UTC),
            manifest_hash="sha256:def",
        )

        assert snapshot.id.startswith("snp_")
        assert snapshot.document_ids == ["doc_a", "doc_b"]
        assert snapshot.index_manifest.index_version == "idx-2026-11-05.1"


class TestSnapshotImmutability:
    """A pinned snapshot is a copy of the corpus manifest, not a live view of it."""

    def test_pinning_does_not_alias_the_caller_document_set(self) -> None:
        document_ids = ["doc_b", "doc_a"]
        manifest = IndexManifest(
            index_version="idx-1",
            embedding_model="text-embedding-3-small",
            searchable_since=datetime(2026, 11, 5, tzinfo=UTC),
            passage_count=2,
        )

        snapshot = CorpusSnapshot.pin(
            label="baseline",
            document_ids=document_ids,
            index_manifest=manifest,
            pinned_at=datetime(2026, 11, 5, 9, 0, tzinfo=UTC),
            manifest_hash="sha256:abc",
        )
        document_ids.append("doc_c")

        assert snapshot.document_ids == ["doc_a", "doc_b"]

    def test_pinned_index_version_is_part_of_the_manifest(self) -> None:
        manifest = IndexManifest(
            index_version="idx-1",
            embedding_model="text-embedding-3-small",
            searchable_since=datetime(2026, 11, 5, tzinfo=UTC),
            passage_count=2,
        )
        snapshot = CorpusSnapshot.pin(
            label="baseline",
            document_ids=[],
            index_manifest=manifest,
            pinned_at=datetime(2026, 11, 5, 9, 0, tzinfo=UTC),
            manifest_hash="sha256:abc",
        )

        assert snapshot.index_manifest is manifest
