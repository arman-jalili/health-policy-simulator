"""Contract freeze: provenance resolution.

`GET /api/v1/passages/{id}` must reproduce the exact slice from the source file. That makes the
published `PassageView`/`ProvenanceView` contract load-bearing for EvidenceRetrieval and
DecisionBrief, so it is frozen here with explicit field names.
"""

from __future__ import annotations

import dataclasses
import inspect
from datetime import date

import httpx
import pytest
from fastapi import FastAPI

import evidence_corpus.domain.published as published_module
from evidence_corpus.application.commands import ResolvePassageRequest
from evidence_corpus.application.services import ResolvePassage
from evidence_corpus.domain.entities import Document
from evidence_corpus.domain.published import PassageView, ProvenanceView
from evidence_corpus.domain.values import Offsets, SpeakerKind

from .contract_helpers import field_names, parameter_names


class TestProvenanceView:
    def test_resolves_outlet_date_page_and_offsets(self) -> None:
        assert field_names(ProvenanceView) == [
            "outlet",
            "published_on",
            "medium",
            "page_from",
            "page_to",
            "offsets",
            "source_uri",
        ]

    def test_is_immutable_so_a_citation_cannot_be_rewritten(self) -> None:
        view = ProvenanceView(
            outlet="Der Standard",
            published_on=date(2026, 10, 1),
            medium="print",
            page_from=3,
            page_to=3,
            offsets=Offsets(120, 240),
            source_uri="s3://corpus/std-2026-10-01.pdf",
        )

        with pytest.raises(dataclasses.FrozenInstanceError):
            view.page_from = 4  # type: ignore[misc]


class TestPassageView:
    def test_matches_the_documented_api_payload(self) -> None:
        names = field_names(PassageView)

        assert {"passage_id", "text", "provenance", "speaker_kind", "citable"} <= set(names)

    def test_carries_its_article_and_document_for_traceability(self) -> None:
        assert {"article_id", "document_id"} <= set(field_names(PassageView))

    def test_speaker_kind_is_exposed_so_consumers_never_re_derive_it(self) -> None:
        assert "speaker_kind" in field_names(PassageView)
        assert SpeakerKind.INSTITUTION.value == "institution"

    def test_view_is_framework_free(self) -> None:
        source = inspect.getsource(published_module)

        assert "import sqlalchemy" not in source
        assert "import pydantic" not in source
        assert "import fastapi" not in source


class TestResolvePassageUseCase:
    def test_signature_is_frozen(self) -> None:
        assert parameter_names(ResolvePassage.execute) == ["self", "request"]
        assert field_names(ResolvePassageRequest) == ["passage_id"]

    def test_returns_the_published_view(self) -> None:
        assert inspect.signature(ResolvePassage.execute).return_annotation == "PassageView"

    def test_repository_exposes_passage_lookup(self) -> None:
        from evidence_corpus.domain.repositories import PassageRepository

        assert "get" in dir(PassageRepository)
        assert "list_by_document" in dir(PassageRepository)


class TestProvenanceResolution:
    """AC 7: the API returns what a reader needs to verify the exact slice from the source."""

    def _document(self) -> Document:
        from datetime import date

        from evidence_corpus.domain.entities import Document, Publication
        from evidence_corpus.domain.values import (
            ExtractionMethod,
            ExtractionQuality,
            LanguageTag,
            SourceType,
        )

        document = Document.register(
            source_uri="s3://corpus/std-2026-10-01.pdf",
            content_hash="sha256:abc",
            publication=Publication("Der Standard", date(2026, 10, 1), "print"),
            source_type=SourceType.PRESS_REPORT,
            language=LanguageTag("de-AT"),
        )
        document.record_extraction(
            "Die Kassenstellen werden aufgestockt.",
            ExtractionQuality(ExtractionMethod.NATIVE, 0.98, 0.0),
        )
        document.drain_events()
        return document

    async def test_resolved_text_is_the_exact_source_slice(self) -> None:
        from evidence_corpus.application.commands import ResolvePassageRequest
        from evidence_corpus.application.read_handlers import ResolvePassageHandler
        from evidence_corpus.domain.values import SpeakerKind
        from evidence_corpus.infrastructure.memory import (
            InMemoryDocumentRepository,
            InMemoryPassageRepository,
        )

        documents = InMemoryDocumentRepository()
        document = self._document()
        await documents.save(document)
        article = document.add_article("Kassenstellen", document.extracted_text or "", 3, 3)
        passage = article.add_passage(
            text="Die Kassenstellen",
            offsets=Offsets(0, 17),
            speaker_kind=SpeakerKind.INSTITUTION,
        )

        view = await ResolvePassageHandler(InMemoryPassageRepository(documents)).execute(
            ResolvePassageRequest(passage_id=passage.id)
        )

        assert document.extracted_text is not None
        assert (
            view.text
            == document.extracted_text[view.provenance.offsets.start : view.provenance.offsets.end]
        )
        assert view.provenance.outlet == "Der Standard"
        assert view.provenance.published_on == date(2026, 10, 1)
        assert (view.provenance.page_from, view.provenance.page_to) == (3, 3)
        assert view.provenance.source_uri == document.source_uri
        assert view.citable is True

    async def test_unknown_passage_is_not_found(self) -> None:
        from evidence_corpus.application.commands import ResolvePassageRequest
        from evidence_corpus.application.read_handlers import ResolvePassageHandler
        from evidence_corpus.domain.errors import PassageNotFound
        from evidence_corpus.infrastructure.memory import (
            InMemoryDocumentRepository,
            InMemoryPassageRepository,
        )

        handler = ResolvePassageHandler(InMemoryPassageRepository(InMemoryDocumentRepository()))

        with pytest.raises(PassageNotFound):
            await handler.execute(ResolvePassageRequest(passage_id="psg_missing"))

    async def test_document_view_summarises_articles_for_inspection(self) -> None:
        from evidence_corpus.application.commands import GetDocumentRequest
        from evidence_corpus.application.read_handlers import GetDocumentHandler
        from evidence_corpus.infrastructure.memory import InMemoryDocumentRepository

        documents = InMemoryDocumentRepository()
        document = self._document()
        await documents.save(document)
        document.add_article("Kassenstellen", document.extracted_text or "", 3, 3)

        view = await GetDocumentHandler(documents).execute(
            GetDocumentRequest(document_id=document.id)
        )

        assert view.document_id == document.id
        assert view.citable is True
        assert [article.headline for article in view.articles] == ["Kassenstellen"]


class TestPassageEndpoint:
    async def test_passage_endpoint_returns_provenance(
        self, app: FastAPI, client: httpx.AsyncClient
    ) -> None:
        from datetime import date

        from evidence_corpus.domain.entities import Document, Publication
        from evidence_corpus.domain.values import (
            ExtractionMethod,
            ExtractionQuality,
            LanguageTag,
            SourceType,
            SpeakerKind,
        )

        document = Document.register(
            source_uri="s3://corpus/std.pdf",
            content_hash="sha256:abc",
            publication=Publication("Der Standard", date(2026, 10, 1), "print"),
            source_type=SourceType.PRESS_REPORT,
            language=LanguageTag("de-AT"),
        )
        document.record_extraction(
            "Die Kassenstellen werden aufgestockt.",
            ExtractionQuality(ExtractionMethod.NATIVE, 0.98, 0.0),
        )
        document.add_article("Kassenstellen", document.extracted_text or "", 3, 3)
        article = document.articles[0]
        passage = article.add_passage(
            text="Die Kassenstellen",
            offsets=Offsets(0, 17),
            speaker_kind=SpeakerKind.INSTITUTION,
        )
        await app.state.corpus.documents.save(document)

        response = await client.get(f"/api/v1/passages/{passage.id}")

        assert response.status_code == 200
        body = response.json()
        assert body["passage_id"] == passage.id
        assert body["provenance"]["outlet"] == "Der Standard"
        assert body["provenance"]["published_on"] == "2026-10-01"
        assert body["provenance"]["page_from"] == 3
        assert body["provenance"]["offsets"] == {"start": 0, "end": 17}
        assert body["speaker_kind"] == "institution"

    async def test_unknown_passage_uses_the_error_envelope(self, client: httpx.AsyncClient) -> None:
        response = await client.get("/api/v1/passages/psg_missing")

        assert response.status_code == 404
        assert response.json()["code"] == "PASSAGE_NOT_FOUND"

    async def test_unknown_document_uses_the_error_envelope(
        self, client: httpx.AsyncClient
    ) -> None:
        response = await client.get("/api/v1/documents/doc_missing")

        assert response.status_code == 404
        assert response.json()["code"] == "DOCUMENT_NOT_FOUND"
