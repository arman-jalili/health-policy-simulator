"""Contract freeze: `IndexIngestedPassages`.

Indexing is a write contract with two obligations: passages become searchable in the same run, and
re-running is idempotent. Withdrawal is explicit (`PassageRevertedFromIndex`) so no later argument
can cite a retracted passage.
"""

from __future__ import annotations

import inspect
from datetime import UTC, datetime

import pytest

from evidence_corpus.application.commands import IndexIngestedPassagesRequest
from evidence_corpus.application.dto import IndexManifestView
from evidence_corpus.application.ports import IndexWriterPort
from evidence_corpus.application.services import IndexIngestedPassages
from evidence_corpus.domain.entities import Document
from evidence_corpus.domain.events import PassageRevertedFromIndex
from evidence_corpus.domain.published import PassageView
from evidence_corpus.domain.values import Offsets, SpeakerKind

from .contract_helpers import field_names, method_names, parameter_names


class TestIndexWriterPort:
    def test_upserts_passages_and_can_withdraw_them(self) -> None:
        assert method_names(IndexWriterPort) == {"upsert_passages", "revert_passage", "search"}

    def test_upsert_is_keyed_by_document_so_reindexing_is_idempotent(self) -> None:
        assert parameter_names(IndexWriterPort.upsert_passages) == [
            "self",
            "document_id",
            "passages",
        ]

    def test_upsert_returns_the_published_index_manifest(self) -> None:
        annotation = inspect.signature(IndexWriterPort.upsert_passages).return_annotation

        assert annotation == "IndexManifestView"

    def test_withdrawal_requires_a_reason(self) -> None:
        assert parameter_names(IndexWriterPort.revert_passage) == [
            "self",
            "passage_id",
            "reason",
        ]

    def test_writer_consumes_published_views_not_orm_rows(self) -> None:
        annotation = (
            inspect.signature(IndexWriterPort.upsert_passages).parameters["passages"].annotation
        )

        assert annotation == "Sequence[PassageView]"


class TestIndexUseCase:
    def test_signature_is_frozen(self) -> None:
        assert parameter_names(IndexIngestedPassages.execute) == ["self", "request"]
        assert field_names(IndexIngestedPassagesRequest) == ["document_id"]

    def test_returns_the_index_manifest_view(self) -> None:
        assert (
            inspect.signature(IndexIngestedPassages.execute).return_annotation
            == "IndexManifestView"
        )

    def test_manifest_view_is_immutable(self) -> None:
        view = IndexManifestView(
            index_version="idx-1",
            embedding_model="text-embedding-3-small",
            searchable_since=datetime(2026, 11, 5, tzinfo=UTC),
            passage_count=1,
        )

        with pytest.raises(AttributeError):
            view.passage_count = 2  # type: ignore[misc]


class TestRetraction:
    def test_reverted_passage_event_is_named_and_auditable(self) -> None:
        assert field_names(PassageRevertedFromIndex) == ["passage_id", "reason"]
        assert PassageRevertedFromIndex.name == "PassageRevertedFromIndex"

    def test_reverted_passage_is_not_deleted_from_the_contract(self) -> None:
        """Withdrawal is a state, not a disappearance: the passage id stays queryable."""
        event = PassageRevertedFromIndex(passage_id="psg_1", reason="retraction")

        assert event.passage_id == "psg_1"


class TestSearchableContract:
    def test_tsvector_and_embedding_are_index_side_concerns(self) -> None:
        assert "tsvector" not in inspect.getsource(IndexWriterPort).lower()
        assert "embedding" not in inspect.getsource(IndexWriterPort).lower()

    def test_published_view_is_the_index_input(self) -> None:
        assert "text" in field_names(PassageView)


class TestIndexingPassages:
    def _document(self) -> Document:
        from datetime import date

        from evidence_corpus.domain.entities import Document, Publication
        from evidence_corpus.domain.values import (
            ExtractionMethod,
            ExtractionQuality,
            LanguageTag,
            SourceType,
        )

        body = "Die Kassenstellen werden aufgestockt. Die Spitalsreform ist beschlossen."
        document = Document.register(
            source_uri="s3://corpus/std.pdf",
            content_hash="sha256:abc",
            publication=Publication("Der Standard", date(2026, 10, 1), "print"),
            source_type=SourceType.PRESS_REPORT,
            language=LanguageTag("de-AT"),
        )
        document.record_extraction(body, ExtractionQuality(ExtractionMethod.NATIVE, 0.99, 0.0))
        article = document.add_article("Kassenstellen", body, 1, 1)
        article.add_passage(
            text="Die Kassenstellen werden aufgestockt.",
            offsets=Offsets(0, 36),
            speaker_kind=SpeakerKind.INSTITUTION,
        )
        article.add_passage(
            text=" Die Spitalsreform ist beschlossen.",
            offsets=Offsets(36, len(body)),
            speaker_kind=SpeakerKind.INSTITUTION,
        )
        document.drain_events()
        return document

    async def test_only_citable_passages_are_indexed_and_reindexing_is_idempotent(self) -> None:
        from evidence_corpus.application.commands import IndexIngestedPassagesRequest
        from evidence_corpus.application.indexing_handler import IndexIngestedPassagesHandler
        from evidence_corpus.infrastructure.events import RecordingEventPublisher
        from evidence_corpus.infrastructure.indexing.memory import InMemoryIndexWriter
        from evidence_corpus.infrastructure.memory import InMemoryDocumentRepository

        documents = InMemoryDocumentRepository()
        document = self._document()
        await documents.save(document)
        writer = InMemoryIndexWriter()
        handler = IndexIngestedPassagesHandler(documents, writer, RecordingEventPublisher())

        first = await handler.execute(IndexIngestedPassagesRequest(document_id=document.id))
        second = await handler.execute(IndexIngestedPassagesRequest(document_id=document.id))

        assert first.passage_count == 2
        assert second.passage_count == 2
        assert await writer.search("Kassenstellen")
        assert len(await writer.search("aufgestockt")) == 1

    async def test_non_citable_document_cannot_be_indexed(self) -> None:
        from datetime import date

        from evidence_corpus.application.commands import IndexIngestedPassagesRequest
        from evidence_corpus.application.indexing_handler import IndexIngestedPassagesHandler
        from evidence_corpus.domain.entities import Document, Publication
        from evidence_corpus.domain.errors import DocumentNotCitable
        from evidence_corpus.domain.values import LanguageTag, SourceType
        from evidence_corpus.infrastructure.events import RecordingEventPublisher
        from evidence_corpus.infrastructure.indexing.memory import InMemoryIndexWriter
        from evidence_corpus.infrastructure.memory import InMemoryDocumentRepository

        documents = InMemoryDocumentRepository()
        document = Document.register(
            source_uri="s3://corpus/raw.pdf",
            content_hash="sha256:raw",
            publication=Publication("Der Standard", date(2026, 10, 1), "print"),
            source_type=SourceType.PRESS_REPORT,
            language=LanguageTag("de-AT"),
        )
        await documents.save(document)

        handler = IndexIngestedPassagesHandler(
            documents, InMemoryIndexWriter(), RecordingEventPublisher()
        )
        with pytest.raises(DocumentNotCitable):
            await handler.execute(IndexIngestedPassagesRequest(document_id=document.id))

    async def test_index_manifest_publication_is_emitted(self) -> None:
        from evidence_corpus.application.commands import IndexIngestedPassagesRequest
        from evidence_corpus.application.indexing_handler import IndexIngestedPassagesHandler
        from evidence_corpus.domain.events import IndexManifestPublished
        from evidence_corpus.infrastructure.events import RecordingEventPublisher
        from evidence_corpus.infrastructure.indexing.memory import InMemoryIndexWriter
        from evidence_corpus.infrastructure.memory import InMemoryDocumentRepository

        documents = InMemoryDocumentRepository()
        document = self._document()
        await documents.save(document)
        publisher = RecordingEventPublisher()

        await IndexIngestedPassagesHandler(documents, InMemoryIndexWriter(), publisher).execute(
            IndexIngestedPassagesRequest(document_id=document.id)
        )

        assert isinstance(publisher.events[0], IndexManifestPublished)
        assert publisher.events[0].passage_count == 2
