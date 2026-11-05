"""Contract freeze: `PinCorpusSnapshot` and `IndexManifest`.

A snapshot is a manifest: it names the documents a run may search and the index version it will
search. Citations stay valid after re-ingestion because passages are immutable and pinned.
"""

from __future__ import annotations

import inspect
from datetime import UTC, datetime

import httpx
import pytest

from evidence_corpus.application.commands import (
    GetCorpusSnapshotRequest,
    PinCorpusSnapshotRequest,
)
from evidence_corpus.application.dto import IndexManifestView, SnapshotView
from evidence_corpus.application.services import PinCorpusSnapshot
from evidence_corpus.domain.entities import CorpusSnapshot, Document, IndexManifest
from evidence_corpus.domain.events import IndexManifestPublished
from evidence_corpus.domain.repositories import CorpusSnapshotRepository

from .contract_helpers import field_names, parameter_names


class TestSnapshotRequest:
    def test_accepts_an_optional_explicit_document_set_and_a_label(self) -> None:
        assert field_names(PinCorpusSnapshotRequest) == ["label", "document_ids"]

    def test_label_is_required_and_documents_are_optional(self) -> None:
        request = PinCorpusSnapshotRequest(label="baseline")

        assert request.document_ids is None

    def test_use_case_returns_the_pinned_snapshot(self) -> None:
        assert parameter_names(PinCorpusSnapshot.execute) == ["self", "request"]
        assert inspect.signature(PinCorpusSnapshot.execute).return_annotation == "SnapshotView"


class TestSnapshotView:
    def test_exposes_the_manifest_hash_for_reproducibility(self) -> None:
        assert {"snapshot_id", "label", "manifest_hash", "pinned_at"} <= set(
            field_names(SnapshotView)
        )

    def test_carries_the_index_version_it_will_search(self) -> None:
        assert "index" in field_names(SnapshotView)

    def test_index_view_names_model_and_activation_time(self) -> None:
        assert field_names(IndexManifestView) == [
            "index_version",
            "embedding_model",
            "searchable_since",
            "passage_count",
        ]


class TestSnapshotAggregate:
    def test_snapshot_is_a_manifest_not_a_transaction_root_for_the_corpus(self) -> None:
        names = field_names(CorpusSnapshot)

        assert "document_ids" in names
        assert "articles" not in names
        assert "passages" not in names

    def test_index_manifest_is_published_as_an_event(self) -> None:
        assert field_names(IndexManifestPublished) == [
            "snapshot_id",
            "index_version",
            "embedding_model",
            "passage_count",
        ]

    def test_event_time_is_explicit(self) -> None:
        manifest = IndexManifest(
            index_version="idx-1",
            embedding_model="text-embedding-3-small",
            searchable_since=datetime(2026, 11, 5, tzinfo=UTC),
            passage_count=10,
        )

        assert manifest.searchable_since.tzinfo is not None


class TestSnapshotRepository:
    def test_is_domain_owned(self) -> None:
        assert getattr(CorpusSnapshotRepository, "_is_protocol", False) is True

    def test_supports_save_and_load_by_id(self) -> None:
        assert {"get", "save"} <= set(dir(CorpusSnapshotRepository))

    def test_document_set_is_resolved_through_the_repository_not_the_manifest(self) -> None:
        assert "list_document_ids" in dir(CorpusSnapshotRepository)

    def test_api_contract_is_created_with_201(self) -> None:
        assert "manifest_hash" in field_names(SnapshotView)


@pytest.mark.parametrize("field", ["snapshot_id", "manifest_hash", "index"])
def test_snapshot_contract_fields_are_present(field: str) -> None:
    assert field in field_names(SnapshotView)


class TestPinCorpusSnapshotHandler:
    def _document(self, suffix: str) -> Document:
        from datetime import date

        from evidence_corpus.domain.entities import Document, Publication
        from evidence_corpus.domain.values import (
            ExtractionMethod,
            ExtractionQuality,
            LanguageTag,
            SourceType,
        )

        document = Document.register(
            source_uri=f"s3://corpus/{suffix}.pdf",
            content_hash=f"sha256:{suffix}",
            publication=Publication("Der Standard", date(2026, 10, 1), "print"),
            source_type=SourceType.PRESS_REPORT,
            language=LanguageTag("de-AT"),
        )
        document.record_extraction(
            "Die Kassenstellen werden aufgestockt.",
            ExtractionQuality(ExtractionMethod.NATIVE, 0.99, 0.0),
        )
        document.drain_events()
        return document

    async def test_reingestion_does_not_change_the_pinned_snapshot(self) -> None:
        from evidence_corpus.application.snapshot_handlers import PinCorpusSnapshotHandler
        from evidence_corpus.infrastructure.events import RecordingEventPublisher
        from evidence_corpus.infrastructure.memory import (
            InMemoryCorpusSnapshotRepository,
            InMemoryDocumentRepository,
        )
        from shared.clock import FixedClock

        documents = InMemoryDocumentRepository()
        first = self._document("a")
        await documents.save(first)
        snapshots = InMemoryCorpusSnapshotRepository()
        clock = FixedClock(datetime(2026, 11, 5, 9, 0, tzinfo=UTC))
        publisher = RecordingEventPublisher()
        handler = PinCorpusSnapshotHandler(documents, snapshots, publisher, clock=clock)

        pinned = await handler.execute(PinCorpusSnapshotRequest(label="baseline"))

        second = self._document("b")
        await documents.save(second)
        reread = await snapshots.get(pinned.snapshot_id)

        assert reread is not None
        assert reread.document_ids == [first.id]
        assert pinned.manifest_hash == reread.manifest_hash

    async def test_explicit_document_set_must_exist(self) -> None:
        from evidence_corpus.application.snapshot_handlers import PinCorpusSnapshotHandler
        from evidence_corpus.domain.errors import DocumentNotFound
        from evidence_corpus.infrastructure.events import RecordingEventPublisher
        from evidence_corpus.infrastructure.memory import (
            InMemoryCorpusSnapshotRepository,
            InMemoryDocumentRepository,
        )

        handler = PinCorpusSnapshotHandler(
            InMemoryDocumentRepository(),
            InMemoryCorpusSnapshotRepository(),
            RecordingEventPublisher(),
        )

        with pytest.raises(DocumentNotFound):
            await handler.execute(
                PinCorpusSnapshotRequest(label="broken", document_ids=["doc_missing"])
            )

    async def test_manifest_hash_covers_documents_and_index_version(self) -> None:
        from evidence_corpus.application.snapshot_handlers import PinCorpusSnapshotHandler
        from evidence_corpus.infrastructure.events import RecordingEventPublisher
        from evidence_corpus.infrastructure.memory import (
            InMemoryCorpusSnapshotRepository,
            InMemoryDocumentRepository,
        )

        documents = InMemoryDocumentRepository()
        await documents.save(self._document("a"))
        handler = PinCorpusSnapshotHandler(
            documents, InMemoryCorpusSnapshotRepository(), RecordingEventPublisher()
        )

        first = await handler.execute(PinCorpusSnapshotRequest(label="one"))

        assert len(first.manifest_hash) == 64
        assert first.index.index_version == "idx-0"

    async def test_index_manifest_publication_is_emitted(self) -> None:
        from evidence_corpus.application.snapshot_handlers import PinCorpusSnapshotHandler
        from evidence_corpus.domain.events import IndexManifestPublished
        from evidence_corpus.infrastructure.events import RecordingEventPublisher
        from evidence_corpus.infrastructure.memory import (
            InMemoryCorpusSnapshotRepository,
            InMemoryDocumentRepository,
        )

        publisher = RecordingEventPublisher()
        handler = PinCorpusSnapshotHandler(
            InMemoryDocumentRepository(), InMemoryCorpusSnapshotRepository(), publisher
        )

        await handler.execute(PinCorpusSnapshotRequest(label="empty"))

        assert isinstance(publisher.events[0], IndexManifestPublished)

    async def test_unknown_snapshot_is_not_found(self) -> None:
        from evidence_corpus.application.snapshot_handlers import GetCorpusSnapshotHandler
        from evidence_corpus.domain.errors import SnapshotNotFound
        from evidence_corpus.infrastructure.memory import InMemoryCorpusSnapshotRepository

        handler = GetCorpusSnapshotHandler(InMemoryCorpusSnapshotRepository())

        with pytest.raises(SnapshotNotFound):
            await handler.execute(GetCorpusSnapshotRequest(snapshot_id="snp_missing"))


class TestSnapshotEndpoints:
    async def test_pin_then_read_snapshot(self, client: httpx.AsyncClient) -> None:
        response = await client.post("/api/v1/corpus/snapshots", json={"label": "baseline"})

        assert response.status_code == 201
        body = response.json()
        assert body["snapshot_id"].startswith("snp_")
        assert len(body["manifest_hash"]) == 64

        read = await client.get(f"/api/v1/corpus/snapshots/{body['snapshot_id']}")

        assert read.status_code == 200
        assert read.json()["label"] == "baseline"
        assert read.json()["index"]["index_version"] == "idx-0"

    async def test_unknown_snapshot_uses_the_error_envelope(
        self, client: httpx.AsyncClient
    ) -> None:
        response = await client.get("/api/v1/corpus/snapshots/snp_missing")

        assert response.status_code == 404
        assert response.json()["code"] == "SNAPSHOT_NOT_FOUND"
