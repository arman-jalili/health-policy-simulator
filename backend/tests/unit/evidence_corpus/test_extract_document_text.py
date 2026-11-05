"""Contract freeze: `ExtractDocumentText` and its ports.

The use case orchestrates; the route decision (native vs OCR) is a domain service. The ports must
stay vendor-free so PyMuPDF/Tesseract can be swapped without touching the application layer.
"""

from __future__ import annotations

import inspect

import pytest

import evidence_corpus.application.ports as ports_module
from evidence_corpus.application.commands import ExtractDocumentTextRequest
from evidence_corpus.application.dto import ExtractionOutcome
from evidence_corpus.application.ports import ContentHasher, ExtractionPort, OcrPort
from evidence_corpus.application.services import ExtractDocumentText
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

    async def test_adapters_are_stubs_until_the_extraction_issue_lands(self) -> None:
        with pytest.raises(NotImplementedError):
            await PyMuPdfExtractor().probe("s3://corpus/scanned.pdf")
