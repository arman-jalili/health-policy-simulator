"""Contract freeze: entities and aggregates of EvidenceCorpus.

Aggregate boundaries are part of the contract: `Document` is per-file (not the corpus),
`IngestionRun` records outcomes and contains no documents, snapshots are manifests.
"""

from __future__ import annotations

import dataclasses
import inspect
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


def _call_for(method: str):  # type: ignore[no-untyped-def]
    def call(stub):  # type: ignore[no-untyped-def]
        if method == "record_extraction":
            stub("text", ExtractionQuality(ExtractionMethod.NATIVE, 0.9, 0.0))
        elif method == "add_article":
            stub("headline", "body", 1, 1)
        elif method == "classify":
            stub(AuthorityTier.PRESS_REPORT)
        else:
            stub()

    return call


def _document() -> Document:
    return Document(
        id="doc_01J0000000000000000000000A",
        source_uri="s3://corpus/std-2026-10-01.pdf",
        content_hash="sha256:abc",
        publication=Publication(
            outlet="Der Standard",
            published_on=date(2026, 10, 1),
            medium="print",
        ),
        source_type=SourceType.PRESS_REPORT,
        language=LanguageTag("de-AT"),
    )


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

    def test_owns_articles_and_events_but_not_the_corpus(self) -> None:
        document = _document()

        assert document.articles == []
        assert document.events == []

    def test_exposes_behaviour_methods_only_no_setters(self) -> None:
        assert {"record_extraction", "add_article", "classify", "is_citable"} <= set(dir(Document))
        setters = [name for name in dir(Document) if name.startswith("set_")]
        assert setters == []

    def test_tier_and_quality_start_unassigned(self) -> None:
        document = _document()

        assert document.tier is None
        assert document.quality is None

    @pytest.mark.parametrize(
        "method",
        ["record_extraction", "add_article", "classify", "is_citable", "publishable_passages"],
    )
    def test_behaviour_is_a_frozen_stub_until_its_issue_lands(self, method: str) -> None:
        document = _document()
        stub = getattr(document, method)

        assert inspect.iscoroutinefunction(stub) is False
        call = _call_for(method)
        with pytest.raises(NotImplementedError):
            call(stub)


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

    def test_publishable_passages_is_a_stub(self) -> None:
        article = Article(
            id="art_01J0000000000000000000000B",
            document_id="doc_01J0000000000000000000000A",
            headline="Kassenstellen",
            body="Text",
            page_from=1,
            page_to=1,
            language=LanguageTag("de-AT"),
        )

        with pytest.raises(NotImplementedError):
            article.publishable_passages()


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

    def test_carries_offsets_and_speaker_kind_not_free_text_bounds(self) -> None:
        passage = Passage(
            id="psg_01J0000000000000000000000C",
            article_id="art_01J0000000000000000000000B",
            document_id="doc_01J0000000000000000000000A",
            ord=0,
            text="Die Kassenstellen werden aufgestockt.",
            offsets=Offsets(0, 42),
            speaker_kind=SpeakerKind.INSTITUTION,
            citable=True,
        )

        assert passage.offsets == Offsets(0, 42)
        assert passage.speaker_kind is SpeakerKind.INSTITUTION
        assert passage.section is ArticleSection.BODY

    def test_provenance_is_attached_for_citation_resolution(self) -> None:
        assert "provenance" in field_names(Passage)


class TestIngestionRun:
    def test_records_outcome_counts_and_owns_no_documents(self) -> None:
        names = field_names(IngestionRun)

        assert names[:3] == ["id", "shard_label", "status"]
        assert {"attempted", "accepted", "quarantined", "failed"} <= set(names)
        assert "documents" not in names

    def test_status_and_outcome_vocabularies_are_frozen(self) -> None:
        assert enum_values(RunStatus) == {"running", "completed", "failed"}
        assert enum_values(IngestionOutcome) == {"accepted", "quarantined", "failed"}

    def test_record_and_complete_are_stubs(self) -> None:
        run = IngestionRun(id="run_01J0000000000000000000000D", shard_label="shard-1")

        with pytest.raises(NotImplementedError):
            run.record(IngestionOutcome.ACCEPTED)
        with pytest.raises(NotImplementedError):
            run.complete()


class TestSnapshotAndIndexManifest:
    def test_snapshot_is_a_manifest_not_a_corpus_root(self) -> None:
        names = field_names(CorpusSnapshot)

        assert names == [
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

    def test_snapshot_pins_documents_plus_index_version(self) -> None:
        manifest = IndexManifest(
            index_version="idx-2026-11-05.1",
            embedding_model="text-embedding-3-small",
            searchable_since=datetime(2026, 11, 5, 9, 0, tzinfo=UTC),
            passage_count=120,
        )
        snapshot = CorpusSnapshot(
            id="snp_01J0000000000000000000000E",
            label="baseline",
            manifest_hash="sha256:def",
            pinned_at=datetime(2026, 11, 5, 9, 5, tzinfo=UTC),
            document_ids=[_document().id],
            index_manifest=manifest,
        )

        assert snapshot.index_manifest.index_version == "idx-2026-11-05.1"
        assert snapshot.document_ids == ["doc_01J0000000000000000000000A"]


class TestProvenanceOnPassage:
    def test_provenance_reuses_the_frozen_locator_bundle(self) -> None:
        passage = Passage(
            id="psg_01J0000000000000000000000F",
            article_id="art_01J0000000000000000000000B",
            document_id="doc_01J0000000000000000000000A",
            ord=0,
            text="Text",
            offsets=Offsets(0, 4),
            speaker_kind=SpeakerKind.INSTITUTION,
            citable=True,
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
