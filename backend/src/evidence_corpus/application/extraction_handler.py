"""`ExtractDocumentText` use case: route, extract, record the measurement.

Canonical: .pi/architecture/modules/evidence-corpus.md

Orchestration only: the route decision is a domain rule, the extraction is a port, and the aggregate
owns the extraction state machine.
"""

from __future__ import annotations

from evidence_corpus.application.commands import ExtractDocumentTextRequest
from evidence_corpus.application.dto import ExtractionOutcome
from evidence_corpus.application.events import EventPublisher
from evidence_corpus.application.ports import ExtractionPort, OcrPort
from evidence_corpus.domain.errors import (
    DocumentNotFound,
    DocumentTooLarge,
    ExtractionFailed,
    OcrUnavailable,
)
from evidence_corpus.domain.repositories import DocumentRepository
from evidence_corpus.domain.rules import PageFactsOcrSelection
from evidence_corpus.domain.values import ExtractionMethod


class ExtractDocumentTextHandler:
    """Implements :class:`evidence_corpus.application.services.ExtractDocumentText`."""

    def __init__(
        self,
        documents: DocumentRepository,
        extraction: ExtractionPort,
        ocr: OcrPort,
        events: EventPublisher,
        selection: PageFactsOcrSelection | None = None,
        actor: str = "system",
        max_pages: int = 500,
    ) -> None:
        self._documents = documents
        self._extraction = extraction
        self._ocr = ocr
        self._events = events
        self._selection = selection or PageFactsOcrSelection()
        self._actor = actor
        self._max_pages = max_pages

    async def execute(self, request: ExtractDocumentTextRequest) -> ExtractionOutcome:
        document = await self._documents.get(request.document_id)
        if document is None:
            raise DocumentNotFound(request.document_id)

        facts = await self._extraction.probe(document.source_uri)
        if facts.page_count > self._max_pages:
            raise DocumentTooLarge(
                f"document has {facts.page_count} pages; limit is {self._max_pages}"
            )
        method = self._selection.select(facts)
        if method is ExtractionMethod.OCR and not _ocr_available(self._ocr):
            raise OcrUnavailable(
                f"OCR is required for {document.source_uri} but the tesseract stack is absent"
            )
        try:
            if method is ExtractionMethod.OCR:
                outcome = await self._ocr.extract(document.source_uri)
            else:
                outcome = await self._extraction.extract(document.source_uri)
        except ExtractionFailed:
            raise
        except Exception as error:
            raise ExtractionFailed(document.source_uri, str(error)) from error

        document.record_extraction(outcome.text, outcome.quality)
        await self._documents.save(document)
        await self._events.publish(document.drain_events(), actor=self._actor, trace_id=None)
        return outcome


def _ocr_available(ocr: OcrPort) -> bool:
    probe = getattr(ocr, "available", None)
    return bool(probe()) if callable(probe) else True
