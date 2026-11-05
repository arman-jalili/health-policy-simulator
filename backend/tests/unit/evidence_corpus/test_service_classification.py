"""Contract freeze: ADR-008 service classification for EvidenceCorpus.

domain services   -> decisions that belong to the business rule
                     (route selection, boundaries, citability)
application       -> use-case orchestration (thin, no business rule)
infrastructure    -> vendor adapters (PyMuPDF, OCR, PostgreSQL index)

The test asserts placement, because a mis-placed service is how layering drifts.
"""

from __future__ import annotations

import inspect

import pytest

from evidence_corpus.application import services as application_services
from evidence_corpus.domain import published, repositories, services
from evidence_corpus.domain.services import (
    ArticleBoundaryStrategy,
    CitabilitySpec,
    NativeVsOcrSelection,
)
from evidence_corpus.domain.values import ExtractionMethod, SpeakerKind
from evidence_corpus.infrastructure.extraction import ocr, pymupdf
from evidence_corpus.infrastructure.indexing import postgres as index_postgres
from evidence_corpus.infrastructure.repository import sqlalchemy as repositories_sqlalchemy

from .contract_helpers import method_names, parameter_names


class TestDomainServices:
    @pytest.mark.parametrize(
        "service",
        [CitabilitySpec, NativeVsOcrSelection, ArticleBoundaryStrategy],
    )
    def test_domain_services_are_protocols_with_declared_methods(self, service: type) -> None:
        assert getattr(service, "_is_protocol", False) is True
        assert method_names(service)

    def test_citability_spec_composes_provenance_quality_and_source_checks(self) -> None:
        assert "is_satisfied" in method_names(CitabilitySpec)
        assert parameter_names(CitabilitySpec.is_satisfied) == [
            "self",
            "document",
            "passage",
        ]

    def test_native_vs_ocr_selection_consumes_page_facts(self) -> None:
        assert "select" in method_names(NativeVsOcrSelection)
        assert (
            inspect.signature(NativeVsOcrSelection.select).return_annotation == "ExtractionMethod"
        )

    def test_article_boundary_strategy_emits_article_drafts(self) -> None:
        assert "segment" in method_names(ArticleBoundaryStrategy)

    def test_domain_layer_declares_no_vendor_dependency(self) -> None:
        source = inspect.getsource(services)

        assert "import pymupdf" not in source
        assert "import sqlalchemy" not in source
        assert "import fastapi" not in source


class TestApplicationServices:
    @pytest.mark.parametrize(
        "service_name",
        [
            "IngestDocument",
            "ExtractDocumentText",
            "SegmentArticle",
            "ClassifySourceAuthority",
            "LinkCanonicalArticle",
            "PinCorpusSnapshot",
            "IndexIngestedPassages",
            "ResolvePassage",
            "GetDocument",
            "StartIngestionRun",
            "GetIngestionRun",
            "GetCorpusSnapshot",
            "ListAuthorityRules",
        ],
    )
    def test_every_use_case_has_an_interface(self, service_name: str) -> None:
        service = getattr(application_services, service_name, None)

        assert service is not None, f"{service_name} is missing from application.services"
        assert getattr(service, "_is_protocol", False) is True
        assert parameter_names(service.execute) == ["self", "request"]

    def test_application_services_own_no_business_rules(self) -> None:
        source = inspect.getsource(application_services)

        assert "class " in source
        assert "_is_protocol" not in source or "Protocol" in source
        assert "raise NotImplementedError" not in source


class TestInfrastructureAdapters:
    def test_extraction_adapters_are_concrete(self) -> None:
        assert hasattr(pymupdf, "PyMuPdfExtractor")
        assert hasattr(ocr, "TesseractOcrExtractor")

    def test_index_writer_is_concrete(self) -> None:
        assert hasattr(index_postgres, "PostgresIndexWriter")

    def test_repository_adapters_are_concrete(self) -> None:
        assert hasattr(repositories_sqlalchemy, "SqlAlchemyDocumentRepository")

    def test_repository_contracts_are_owned_by_the_domain(self) -> None:
        assert getattr(repositories.DocumentRepository, "_is_protocol", False) is True
        assert getattr(repositories.CorpusSnapshotRepository, "_is_protocol", False) is True


class TestPublishedLanguage:
    def test_published_views_exist_for_consumers(self) -> None:
        assert hasattr(published, "PassageView")
        assert hasattr(published, "ProvenanceView")

    def test_published_views_do_not_expose_orm_or_framework_types(self) -> None:
        source = inspect.getsource(published)

        assert "import sqlalchemy" not in source
        assert "import pydantic" not in source
        assert "import fastapi" not in source


class TestExecutableDomainRules:
    """The domain rules behind the ports, executed without a database or a vendor library."""

    def test_page_facts_route_scans_and_empty_pages_to_ocr(self) -> None:
        from evidence_corpus.domain.rules import PageFactsOcrSelection
        from evidence_corpus.domain.values import PageTextFacts

        selection = PageFactsOcrSelection()

        assert (
            selection.select(
                PageTextFacts(has_text_layer=False, average_chars_per_page=0, missing_glyph_rate=0)
            )
            is ExtractionMethod.OCR
        )
        assert (
            selection.select(
                PageTextFacts(has_text_layer=True, average_chars_per_page=12, missing_glyph_rate=0)
            )
            is ExtractionMethod.OCR
        )
        assert (
            selection.select(
                PageTextFacts(
                    has_text_layer=True, average_chars_per_page=2500, missing_glyph_rate=0.4
                )
            )
            is ExtractionMethod.OCR
        )

    def test_page_facts_route_a_clean_text_layer_to_native(self) -> None:
        from evidence_corpus.domain.rules import PageFactsOcrSelection
        from evidence_corpus.domain.values import PageTextFacts

        facts = PageTextFacts(
            has_text_layer=True, average_chars_per_page=2500, missing_glyph_rate=0.01
        )

        assert PageFactsOcrSelection().select(facts) is ExtractionMethod.NATIVE

    def test_citability_spec_requires_document_quality_passage_citability_and_provenance(
        self,
    ) -> None:
        from datetime import date

        from evidence_corpus.domain.entities import Document, Passage, Publication
        from evidence_corpus.domain.rules import DefaultCitabilitySpec
        from evidence_corpus.domain.values import (
            ExtractionQuality,
            LanguageTag,
            Offsets,
            Provenance,
            SourceType,
        )

        spec = DefaultCitabilitySpec()
        document = Document.register(
            source_uri="s3://corpus/std.pdf",
            content_hash="sha256:abc",
            publication=Publication("Der Standard", date(2026, 10, 1), "print"),
            source_type=SourceType.PRESS_REPORT,
            language=LanguageTag("de-AT"),
        )
        passage = Passage.new(
            article_id="art_1",
            document_id=document.id,
            ord=0,
            text="Text",
            offsets=Offsets(0, 4),
            speaker_kind=SpeakerKind.INSTITUTION,
        )

        assert spec.is_satisfied(document, passage) is False

        document.record_extraction("Text", ExtractionQuality(ExtractionMethod.NATIVE, 0.99, 0.0))
        assert spec.is_satisfied(document, passage) is False

        passage.provenance = Provenance(
            outlet="Der Standard",
            published_on=date(2026, 10, 1),
            medium="print",
            page_from=1,
            page_to=1,
            offsets=Offsets(0, 4),
            source_uri="s3://corpus/std.pdf",
        )
        assert spec.is_satisfied(document, passage) is True

    def test_citability_spec_refuses_person_attributed_spans(self) -> None:
        from datetime import date

        from evidence_corpus.domain.entities import Document, Passage, Publication
        from evidence_corpus.domain.rules import DefaultCitabilitySpec
        from evidence_corpus.domain.values import (
            ExtractionQuality,
            LanguageTag,
            Offsets,
            Provenance,
            SourceType,
        )

        document = Document.register(
            source_uri="s3://corpus/std.pdf",
            content_hash="sha256:abc",
            publication=Publication("Der Standard", date(2026, 10, 1), "print"),
            source_type=SourceType.PRESS_REPORT,
            language=LanguageTag("de-AT"),
        )
        document.record_extraction("Text", ExtractionQuality(ExtractionMethod.NATIVE, 0.99, 0.0))
        passage = Passage.new(
            article_id="art_1",
            document_id=document.id,
            ord=0,
            text="Zitat",
            offsets=Offsets(0, 5),
            speaker_kind=SpeakerKind.PERSON,
            provenance=Provenance(
                outlet="Der Standard",
                published_on=date(2026, 10, 1),
                medium="print",
                page_from=1,
                page_to=1,
                offsets=Offsets(0, 5),
                source_uri="s3://corpus/std.pdf",
            ),
        )

        assert DefaultCitabilitySpec().is_satisfied(document, passage) is False
