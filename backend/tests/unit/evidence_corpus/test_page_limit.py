"""Unit: a document above the configured page budget is refused before extraction (#424)."""

from __future__ import annotations

from datetime import date

import pytest

from evidence_corpus.application.commands import ExtractDocumentTextRequest
from evidence_corpus.application.extraction_handler import ExtractDocumentTextHandler
from evidence_corpus.domain.entities import Document, Publication
from evidence_corpus.domain.errors import DocumentTooLarge
from evidence_corpus.domain.values import LanguageTag, PageTextFacts, SourceType
from evidence_corpus.infrastructure.events import RecordingEventPublisher
from evidence_corpus.infrastructure.memory import InMemoryDocumentRepository


class _ProbeOnly:
    async def probe(self, source_uri: str) -> PageTextFacts:
        return PageTextFacts(True, 100.0, 0.0, page_count=501)

    async def extract(self, source_uri: str) -> object:
        raise AssertionError("extraction must not start above the page limit")


async def test_page_limit_is_checked_before_extraction() -> None:
    repository = InMemoryDocumentRepository()
    document = Document.register(
        source_uri="s3://corpus/too-large.pdf",
        content_hash="sha256:too-large",
        publication=Publication("Der Standard", date(2026, 10, 1), "print"),
        source_type=SourceType.PRESS_REPORT,
        language=LanguageTag("de-AT"),
    )
    await repository.save(document)
    handler = ExtractDocumentTextHandler(
        repository,
        _ProbeOnly(),  # type: ignore[arg-type]
        _ProbeOnly(),  # type: ignore[arg-type]
        RecordingEventPublisher(),
        max_pages=500,
    )

    with pytest.raises(DocumentTooLarge, match="501 pages"):
        await handler.execute(ExtractDocumentTextRequest(document_id=document.id))
