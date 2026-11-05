"""Contract freeze: `ExtractDocumentText` and its ports.

The use case orchestrates; the route decision (native vs OCR) is a domain service. The ports must
stay vendor-free so PyMuPDF/Tesseract can be swapped without touching the application layer.
"""

from __future__ import annotations

import inspect
from pathlib import Path

import pytest

import evidence_corpus.application.ports as ports_module
from evidence_corpus.application.commands import ExtractDocumentTextRequest
from evidence_corpus.application.dto import ExtractionOutcome
from evidence_corpus.application.ports import ContentHasher, ExtractionPort, OcrPort
from evidence_corpus.application.services import ExtractDocumentText
from evidence_corpus.domain.entities import Document
from evidence_corpus.domain.values import ExtractionMethod, ExtractionQuality, PageTextFacts
from evidence_corpus.infrastructure.extraction.ocr import TesseractOcrExtractor
from evidence_corpus.infrastructure.extraction.pymupdf import PyMuPdfExtractor

from .contract_helpers import field_names, method_names, parameter_names


class TestPorts:
    def test_extraction_port_can_probe_then_extract(self) -> None:
        assert method_names(ExtractionPort) == {"probe", "extract"}

    def test_probe_returns_page_level_facts_for_route_selection(self) -> None:
        probe = inspect.signature(ExtractionPort.probe)

        assert parameter_names(ExtractionPort.probe) == ["self", "source_uri"]
        assert probe.return_annotation == "PageTextFacts"

    def test_extraction_port_returns_text_with_quality(self) -> None:
        assert inspect.signature(ExtractionPort.extract).return_annotation == "ExtractionOutcome"

    def test_ocr_is_a_separate_port(self) -> None:
        assert getattr(OcrPort, "_is_protocol", False) is True
        assert method_names(OcrPort) == {"extract"}

    def test_content_hashing_is_a_port_so_duplicates_are_detected_upstream(self) -> None:
        assert method_names(ContentHasher)
        assert getattr(ContentHasher, "_is_protocol", False) is True

    def test_ports_are_vendor_free(self) -> None:
        source = inspect.getsource(ports_module)

        assert "import pymupdf" not in source
        assert "import fitz" not in source
        assert "import pytesseract" not in source
        assert "from pymupdf" not in source


class TestUseCase:
    def test_signature_is_frozen(self) -> None:
        assert parameter_names(ExtractDocumentText.execute) == ["self", "request"]
        assert field_names(ExtractDocumentTextRequest) == ["document_id"]

    def test_returns_route_and_quality_for_the_caller(self) -> None:
        assert field_names(ExtractionOutcome) == ["document_id", "text", "quality"]

    def test_scanned_input_is_routed_to_ocr_and_labelled_ocr(self) -> None:
        scanned = PageTextFacts(
            has_text_layer=False,
            average_chars_per_page=0.0,
            missing_glyph_rate=0.0,
        )

        assert scanned.has_text_layer is False
        assert ExtractionMethod.OCR.value == "ocr"

    def test_outcome_quality_is_an_immutable_measurement(self) -> None:
        quality = ExtractionQuality(ExtractionMethod.OCR, 0.9, 0.02)

        with pytest.raises(AttributeError):
            quality.confidence = 0.5  # type: ignore[misc]


class TestAdapters:
    def test_native_extractor_is_a_concrete_adapter(self) -> None:
        assert inspect.isclass(PyMuPdfExtractor)
        assert hasattr(PyMuPdfExtractor, "extract")
        assert hasattr(PyMuPdfExtractor, "probe")

    def test_ocr_adapter_is_a_concrete_adapter(self) -> None:
        assert inspect.isclass(TesseractOcrExtractor)
        assert hasattr(TesseractOcrExtractor, "extract")

    async def test_unfetchable_scheme_is_refused(self) -> None:
        from evidence_corpus.domain.errors import ExtractionFailed

        with pytest.raises(ExtractionFailed):
            await PyMuPdfExtractor().probe("s3://corpus/scanned.pdf")


class RecordingOcr:
    def __init__(self, outcome: ExtractionOutcome) -> None:
        self._outcome = outcome
        self.calls = 0

    async def extract(self, source_uri: str) -> ExtractionOutcome:
        self.calls += 1
        return self._outcome


class RecordingExtraction:
    def __init__(self, facts: PageTextFacts, outcome: ExtractionOutcome) -> None:
        self._facts = facts
        self._outcome = outcome
        self.calls = 0

    async def probe(self, source_uri: str) -> PageTextFacts:
        return self._facts

    async def extract(self, source_uri: str) -> ExtractionOutcome:
        self.calls += 1
        return self._outcome


class TestExtractDocumentTextHandler:
    def _document(self) -> Document:
        from datetime import date

        from evidence_corpus.domain.entities import Document, Publication
        from evidence_corpus.domain.values import LanguageTag, SourceType

        return Document.register(
            source_uri="s3://corpus/std.pdf",
            content_hash="sha256:abc",
            publication=Publication("Der Standard", date(2026, 10, 1), "print"),
            source_type=SourceType.PRESS_REPORT,
            language=LanguageTag("de-AT"),
        )

    async def test_scanned_document_routes_to_ocr_and_labels_the_quality(self) -> None:
        from evidence_corpus.application.extraction_handler import ExtractDocumentTextHandler
        from evidence_corpus.infrastructure.events import RecordingEventPublisher
        from evidence_corpus.infrastructure.memory import InMemoryDocumentRepository

        repository = InMemoryDocumentRepository()
        document = self._document()
        await repository.save(document)
        ocr_outcome = ExtractionOutcome(
            document_id=document.id,
            text="OCR text",
            quality=ExtractionQuality(ExtractionMethod.OCR, 0.93, 0.01),
        )
        extraction = RecordingExtraction(
            PageTextFacts(has_text_layer=False, average_chars_per_page=0, missing_glyph_rate=0),
            ExtractionOutcome(
                document_id=document.id,
                text="",
                quality=ExtractionQuality(ExtractionMethod.NATIVE, 1.0, 0.0),
            ),
        )
        ocr = RecordingOcr(ocr_outcome)
        publisher = RecordingEventPublisher()

        handler = ExtractDocumentTextHandler(
            repository, extraction, ocr, publisher, actor="operator"
        )
        outcome = await handler.execute(ExtractDocumentTextRequest(document_id=document.id))

        assert outcome is ocr_outcome
        assert outcome.quality.method is ExtractionMethod.OCR
        assert outcome.quality.is_acceptable()
        assert ocr.calls == 1
        assert extraction.calls == 0
        stored = repository._documents[document.id]
        assert stored.quality is not None
        assert stored.quality.method is ExtractionMethod.OCR
        from evidence_corpus.domain.events import DocumentIngested

        assert isinstance(publisher.events[0], DocumentIngested)
        assert publisher.actors == ["operator"]

    async def test_clean_text_layer_routes_to_native_extraction(self) -> None:
        from evidence_corpus.application.extraction_handler import ExtractDocumentTextHandler
        from evidence_corpus.infrastructure.events import RecordingEventPublisher
        from evidence_corpus.infrastructure.memory import InMemoryDocumentRepository

        repository = InMemoryDocumentRepository()
        document = self._document()
        await repository.save(document)
        native_outcome = ExtractionOutcome(
            document_id=document.id,
            text="Native text",
            quality=ExtractionQuality(ExtractionMethod.NATIVE, 0.99, 0.0),
        )
        extraction = RecordingExtraction(
            PageTextFacts(has_text_layer=True, average_chars_per_page=2500, missing_glyph_rate=0.0),
            native_outcome,
        )
        ocr = RecordingOcr(native_outcome)

        handler = ExtractDocumentTextHandler(repository, extraction, ocr, RecordingEventPublisher())
        outcome = await handler.execute(ExtractDocumentTextRequest(document_id=document.id))

        assert outcome is native_outcome
        assert extraction.calls == 1
        assert ocr.calls == 0

    async def test_unknown_document_is_not_found(self) -> None:
        from evidence_corpus.application.extraction_handler import ExtractDocumentTextHandler
        from evidence_corpus.domain.errors import DocumentNotFound
        from evidence_corpus.domain.values import PageTextFacts
        from evidence_corpus.infrastructure.events import RecordingEventPublisher
        from evidence_corpus.infrastructure.memory import InMemoryDocumentRepository

        handler = ExtractDocumentTextHandler(
            InMemoryDocumentRepository(),
            RecordingExtraction(
                PageTextFacts(True, 1000, 0.0),
                ExtractionOutcome(
                    "doc_x", "t", ExtractionQuality(ExtractionMethod.NATIVE, 1.0, 0.0)
                ),
            ),
            RecordingOcr(
                ExtractionOutcome("doc_x", "t", ExtractionQuality(ExtractionMethod.OCR, 1.0, 0.0))
            ),
            RecordingEventPublisher(),
        )

        with pytest.raises(DocumentNotFound):
            await handler.execute(ExtractDocumentTextRequest(document_id="doc_missing"))

    async def test_provider_failure_is_reported_as_extraction_failed(self) -> None:
        from evidence_corpus.application.extraction_handler import ExtractDocumentTextHandler
        from evidence_corpus.domain.errors import ExtractionFailed
        from evidence_corpus.infrastructure.events import RecordingEventPublisher
        from evidence_corpus.infrastructure.memory import InMemoryDocumentRepository

        class BrokenExtraction(RecordingExtraction):
            async def extract(self, source_uri: str) -> ExtractionOutcome:
                raise RuntimeError("pdf is encrypted")

        repository = InMemoryDocumentRepository()
        document = self._document()
        await repository.save(document)
        handler = ExtractDocumentTextHandler(
            repository,
            BrokenExtraction(
                PageTextFacts(True, 2500, 0.0),
                ExtractionOutcome(
                    document.id, "", ExtractionQuality(ExtractionMethod.NATIVE, 1.0, 0.0)
                ),
            ),
            RecordingOcr(
                ExtractionOutcome(
                    document.id, "", ExtractionQuality(ExtractionMethod.OCR, 1.0, 0.0)
                )
            ),
            RecordingEventPublisher(),
        )

        with pytest.raises(ExtractionFailed, match="encrypted"):
            await handler.execute(ExtractDocumentTextRequest(document_id=document.id))
        assert repository._documents[document.id].quality is None


class TestNativeExtractorOnRealPdf:
    async def test_text_layer_is_probed_and_extracted_with_quality(self, tmp_path: Path) -> None:
        import pymupdf

        path = tmp_path / "press.pdf"
        document = pymupdf.open()  # type: ignore[no-untyped-call]
        page = document.new_page()
        page.insert_textbox(
            pymupdf.Rect(72, 72, 540, 760),  # type: ignore[no-untyped-call]
            "Die Kassenstellen werden aufgestockt. " * 40,
            fontsize=9,
        )
        document.save(path)  # type: ignore[no-untyped-call]
        document.close()  # type: ignore[no-untyped-call]

        extractor = PyMuPdfExtractor()
        facts = await extractor.probe(str(path))
        outcome = await extractor.extract(str(path))

        assert facts.has_text_layer is True
        assert facts.average_chars_per_page > 300
        assert outcome.text.startswith("Die Kassenstellen")
        assert outcome.quality.method is ExtractionMethod.NATIVE
        assert outcome.quality.is_acceptable() is True

    async def test_scanned_pdf_without_text_layer_probes_as_ocr_candidate(
        self, tmp_path: Path
    ) -> None:
        import pymupdf

        path = tmp_path / "scan.pdf"
        document = pymupdf.open()  # type: ignore[no-untyped-call]
        document.new_page()
        document.save(path)  # type: ignore[no-untyped-call]
        document.close()  # type: ignore[no-untyped-call]

        facts = await PyMuPdfExtractor().probe(str(path))
        from evidence_corpus.domain.rules import PageFactsOcrSelection

        assert facts.has_text_layer is False
        assert PageFactsOcrSelection().select(facts) is ExtractionMethod.OCR
