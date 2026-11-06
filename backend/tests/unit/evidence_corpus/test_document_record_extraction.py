"""Contract freeze: `Document.record_extraction` and the extraction state machine errors.

Invariant 2 (assigned once, immutable) and invariant 4 (quality gate) are enforced by the
aggregate. The contract fixes the method signature, the failure modes and the emitted events;
the implementation issue owns the behaviour.
"""

from __future__ import annotations

import inspect

import pytest

from evidence_corpus.application.commands import ExtractDocumentTextRequest
from evidence_corpus.application.dto import ExtractionOutcome
from evidence_corpus.application.services import ExtractDocumentText
from evidence_corpus.domain.entities import Document
from evidence_corpus.domain.errors import (
    AlreadyExtracted,
    AuthorityAlreadyAssigned,
    DocumentNotCitable,
    ExtractionFailed,
)
from evidence_corpus.domain.events import (
    DocumentExtractionFailed,
    DocumentIngested,
    DocumentQuarantined,
)
from evidence_corpus.domain.values import (
    AuthorityTier,
    ExtractionMethod,
    ExtractionQuality,
    SourceType,
)

from .contract_helpers import field_names, parameter_names


class TestRecordExtractionSignature:
    def test_accepts_text_and_quality_and_returns_nothing(self) -> None:
        signature = inspect.signature(Document.record_extraction)

        assert parameter_names(Document.record_extraction) == ["self", "text", "quality"]
        assert signature.return_annotation in (None, "None")

    def test_mutation_goes_through_behaviour_not_setters(self) -> None:
        setters = {name for name in dir(Document) if name.startswith("set_")}

        assert setters == set()
        assert "record_extraction" in dir(Document)

    def test_extraction_state_is_publicly_readable_for_citability_checks(self) -> None:
        assert {"quality", "tier", "is_citable"} <= set(dir(Document))


class TestRecordExtractionFailureModes:
    def test_second_extraction_is_a_conflict(self) -> None:
        error = AlreadyExtracted("doc_01J0000000000000000000000A")

        assert error.code == "ALREADY_EXTRACTED"
        assert error.status_code == 409

    def test_authority_cannot_be_reassigned(self) -> None:
        error = AuthorityAlreadyAssigned("doc_01J0000000000000000000000A")

        assert error.code == "AUTHORITY_ALREADY_ASSIGNED"
        assert error.status_code == 409

    def test_quarantined_document_cannot_segment_articles(self) -> None:
        error = DocumentNotCitable("doc_01J0000000000000000000000A")

        assert error.code == "DOCUMENT_NOT_CITABLE"
        assert error.status_code == 409

    def test_quarantine_reason_carries_the_measured_quality(self) -> None:
        from evidence_corpus.domain.values import ExtractionMethod, ExtractionQuality

        error = DocumentNotCitable(
            "doc_01J0000000000000000000000A",
            quality=ExtractionQuality(ExtractionMethod.NATIVE, 0.46, 0.0, page_count=1),
            characters=31,
        )

        assert "quality 0.46 < 0.85" in str(error)
        assert "(1 page, 31 chars)" in str(error)

    def test_extraction_failure_is_reported_not_swallowed(self) -> None:
        error = ExtractionFailed("scanned.pdf", "ocr backend unavailable")

        assert error.code == "EXTRACTION_FAILED"
        assert error.status_code == 422
        assert "scanned.pdf" in str(error)


class TestExtractionEvents:
    def test_document_ingested_payload_is_frozen(self) -> None:
        assert field_names(DocumentIngested) == [
            "document_id",
            "source_uri",
            "content_hash",
            "quality_method",
        ]
        assert DocumentIngested.name == "DocumentIngested"

    def test_document_quarantined_records_quality_and_threshold(self) -> None:
        assert field_names(DocumentQuarantined) == ["document_id", "quality", "threshold"]
        assert DocumentQuarantined.name == "DocumentQuarantined"

    def test_extraction_failure_records_method_and_reason(self) -> None:
        assert field_names(DocumentExtractionFailed) == ["document_id", "method", "reason"]

    def test_quality_method_is_part_of_the_published_payload(self) -> None:
        event = DocumentIngested(
            document_id="doc_01J0000000000000000000000A",
            source_uri="s3://corpus/std.pdf",
            content_hash="sha256:abc",
            quality_method=ExtractionMethod.NATIVE,
        )

        assert event.quality_method is ExtractionMethod.NATIVE


class TestExtractDocumentTextContract:
    def test_use_case_takes_a_document_id_request(self) -> None:
        assert parameter_names(ExtractDocumentText.execute) == ["self", "request"]
        assert field_names(ExtractDocumentTextRequest) == ["document_id"]

    def test_use_case_returns_text_plus_measured_quality(self) -> None:
        assert field_names(ExtractionOutcome) == ["document_id", "text", "quality"]

    def test_quality_records_the_route_that_was_used(self) -> None:
        outcome = ExtractionOutcome(
            document_id="doc_01J0000000000000000000000A",
            text="Auszug",
            quality=ExtractionQuality(
                method=ExtractionMethod.OCR,
                confidence=0.91,
                missing_glyph_rate=0.01,
            ),
        )

        assert outcome.quality.method is ExtractionMethod.OCR


def test_conflict_codes_are_unique_across_the_module() -> None:
    codes = [AlreadyExtracted.code, AuthorityAlreadyAssigned.code, DocumentNotCitable.code]

    assert len(set(codes)) == len(codes)
    assert all(code.isupper() for code in codes)


def _document() -> Document:
    from datetime import date

    from evidence_corpus.domain.entities import Publication
    from evidence_corpus.domain.values import LanguageTag

    return Document.register(
        source_uri="s3://corpus/std.pdf",
        content_hash="sha256:abc",
        publication=Publication("Der Standard", date(2026, 10, 1), "print"),
        source_type=SourceType.PRESS_REPORT,
        language=LanguageTag("de-AT"),
    )


GOOD_QUALITY = ExtractionQuality(ExtractionMethod.NATIVE, 0.97, 0.0)
POOR_QUALITY = ExtractionQuality(ExtractionMethod.OCR, 0.35, 0.6)


class TestExtractionStateIsAssignedOnce:
    """Invariant 2: extraction outcome and authority are assigned at ingestion and immutable."""

    def test_reclassification_attempt_leaves_tier_and_quality_unchanged(self) -> None:
        document = _document()
        document.record_extraction("Text", GOOD_QUALITY)
        document.classify(AuthorityTier.PRESS_REPORT)

        with pytest.raises(AlreadyExtracted):
            document.record_extraction("Anderer Text", POOR_QUALITY)
        with pytest.raises(AuthorityAlreadyAssigned):
            document.classify(AuthorityTier.LEGISLATION)

        assert document.quality is GOOD_QUALITY
        assert document.extracted_text == "Text"
        assert document.tier is AuthorityTier.PRESS_REPORT

    def test_quarantined_document_keeps_the_text_for_diagnostics(self) -> None:
        document = _document()

        document.record_extraction("garbled text", POOR_QUALITY)

        assert document.extracted_text == "garbled text"
        assert document.is_citable() is False
        with pytest.raises(DocumentNotCitable):
            document.add_article("headline", "body", 1, 1)

    def test_events_are_drained_once(self) -> None:
        document = _document()
        document.record_extraction("Text", GOOD_QUALITY)

        first = document.drain_events()
        second = document.drain_events()

        assert len(first) == 1
        assert second == []

    def test_accepted_extraction_emits_ingested_not_quarantined(self) -> None:
        document = _document()

        document.record_extraction("Text", GOOD_QUALITY)

        event = document.drain_events()[0]
        assert isinstance(event, DocumentIngested)
        assert event.document_id == document.id
        assert event.source_uri == document.source_uri
        assert event.content_hash == document.content_hash
