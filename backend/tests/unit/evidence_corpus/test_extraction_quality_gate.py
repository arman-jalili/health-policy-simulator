"""Contract freeze: the extraction quality gate.

The gate is a measurement, not a heuristic bolted onto the API: `ExtractionQuality` carries the
evidence (method, confidence, glyph rate) and the acceptance threshold is a frozen contract value.
"""

from __future__ import annotations

import inspect

import pytest

from evidence_corpus.domain.entities import Document
from evidence_corpus.domain.events import DocumentQuarantined
from evidence_corpus.domain.services import NativeVsOcrSelection
from evidence_corpus.domain.values import (
    DEFAULT_MINIMUM_CONFIDENCE,
    ExtractionMethod,
    ExtractionQuality,
    PageTextFacts,
)

from .contract_helpers import field_names, method_names, parameter_names


class TestQualityMeasurement:
    def test_confidence_and_glyph_rate_are_both_required(self) -> None:
        quality = ExtractionQuality(
            method=ExtractionMethod.OCR,
            confidence=0.72,
            missing_glyph_rate=0.18,
        )

        assert quality.confidence == pytest.approx(0.72)
        assert quality.missing_glyph_rate == pytest.approx(0.18)

    def test_gate_accepts_a_per_call_threshold(self) -> None:
        assert parameter_names(ExtractionQuality.is_acceptable) == [
            "self",
            "minimum_confidence",
        ]

    def test_default_threshold_is_part_of_the_contract(self) -> None:
        assert pytest.approx(0.85) == DEFAULT_MINIMUM_CONFIDENCE


class TestGateOutcome:
    def test_below_threshold_is_quarantine_not_deletion(self) -> None:
        event = DocumentQuarantined(
            document_id="doc_01J0000000000000000000000A",
            quality=ExtractionQuality(ExtractionMethod.OCR, 0.4, 0.5),
            threshold=DEFAULT_MINIMUM_CONFIDENCE,
        )

        assert event.threshold == DEFAULT_MINIMUM_CONFIDENCE
        assert event.quality.method is ExtractionMethod.OCR

    def test_quarantine_event_is_named_in_past_tense(self) -> None:
        assert DocumentQuarantined.name == "DocumentQuarantined"

    def test_quarantined_documents_still_expose_publishable_passages(self) -> None:
        assert "publishable_passages" in dir(Document)
        assert field_names(DocumentQuarantined) == ["document_id", "quality", "threshold"]


class TestRouteSelection:
    def test_selection_is_a_domain_service_not_an_adapter(self) -> None:
        assert getattr(NativeVsOcrSelection, "_is_protocol", False) is True
        assert method_names(NativeVsOcrSelection) == {"select"}

    def test_selection_receives_page_level_facts(self) -> None:
        assert parameter_names(NativeVsOcrSelection.select) == ["self", "page_facts"]

    def test_page_facts_track_text_layer_and_glyph_damage(self) -> None:
        facts = PageTextFacts(
            has_text_layer=False,
            average_chars_per_page=0.0,
            missing_glyph_rate=1.0,
        )

        assert facts.has_text_layer is False

    def test_scanned_inputs_are_identified_by_absence_of_a_text_layer(self) -> None:
        assert "has_text_layer" in field_names(PageTextFacts)

    def test_ocr_is_a_first_class_extraction_method(self) -> None:
        assert ExtractionMethod.OCR.value == "ocr"
        assert inspect.isclass(ExtractionMethod)


class TestGatePrecision:
    """The gate is a measurement with a frozen threshold, not a vibe check."""

    def test_threshold_is_inclusive(self) -> None:
        at_threshold = ExtractionQuality(ExtractionMethod.OCR, DEFAULT_MINIMUM_CONFIDENCE, 0.0)
        below_threshold = ExtractionQuality(
            ExtractionMethod.OCR, DEFAULT_MINIMUM_CONFIDENCE - 0.01, 0.0
        )

        assert at_threshold.is_acceptable() is True
        assert below_threshold.is_acceptable() is False

    def test_glyph_damage_is_inclusive(self) -> None:
        from evidence_corpus.domain.values import MAX_MISSING_GLYPH_RATE

        at_limit = ExtractionQuality(ExtractionMethod.OCR, 0.99, MAX_MISSING_GLYPH_RATE)
        beyond_limit = ExtractionQuality(ExtractionMethod.OCR, 0.99, MAX_MISSING_GLYPH_RATE + 0.01)

        assert at_limit.is_acceptable() is True
        assert beyond_limit.is_acceptable() is False

    def test_caller_can_tighten_the_threshold_for_legal_sources(self) -> None:
        quality = ExtractionQuality(ExtractionMethod.OCR, 0.9, 0.0)

        assert quality.is_acceptable() is True
        assert quality.is_acceptable(minimum_confidence=0.95) is False

    def test_quarantine_is_recorded_with_the_quality_and_threshold(self) -> None:
        from datetime import date

        from evidence_corpus.domain.entities import Document, Publication
        from evidence_corpus.domain.events import DocumentQuarantined
        from evidence_corpus.domain.values import LanguageTag, SourceType

        document = Document.register(
            source_uri="s3://corpus/scan.pdf",
            content_hash="sha256:def",
            publication=Publication("Der Standard", date(2026, 10, 1), "print"),
            source_type=SourceType.PRESS_REPORT,
            language=LanguageTag("de-AT"),
        )
        quality = ExtractionQuality(ExtractionMethod.OCR, 0.3, 0.7)

        document.record_extraction("garbled", quality)

        event = document.drain_events()[0]
        assert isinstance(event, DocumentQuarantined)
        assert event.quality is quality
        assert event.threshold == DEFAULT_MINIMUM_CONFIDENCE

    def test_quarantined_document_publishes_no_passages(self) -> None:
        from datetime import date

        from evidence_corpus.domain.entities import Document, Publication
        from evidence_corpus.domain.values import LanguageTag, SourceType

        document = Document.register(
            source_uri="s3://corpus/scan.pdf",
            content_hash="sha256:def",
            publication=Publication("Der Standard", date(2026, 10, 1), "print"),
            source_type=SourceType.PRESS_REPORT,
            language=LanguageTag("de-AT"),
        )
        document.record_extraction("garbled", ExtractionQuality(ExtractionMethod.OCR, 0.3, 0.7))

        assert document.publishable_passages() == []
