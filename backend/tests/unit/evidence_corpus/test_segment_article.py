"""Contract freeze: `SegmentArticle` and the boundary strategies.

A clipping digest and a single article are genuinely different segmentation rules, hence Strategy.
The contract fixes the strategy port, the draft it emits and the event that records the outcome.
"""

from __future__ import annotations

import inspect

import pytest

from evidence_corpus.application.commands import SegmentArticleRequest
from evidence_corpus.application.dto import SegmentationResult
from evidence_corpus.application.services import SegmentArticle
from evidence_corpus.domain.entities import Document, Publication
from evidence_corpus.domain.events import ArticleSegmented
from evidence_corpus.domain.services import ArticleBoundaryStrategy
from evidence_corpus.domain.values import ArticleDraft

from .contract_helpers import field_names, method_names, parameter_names


class TestBoundaryStrategy:
    def test_is_a_domain_service_with_one_operation(self) -> None:
        assert getattr(ArticleBoundaryStrategy, "_is_protocol", False) is True
        assert method_names(ArticleBoundaryStrategy) == {"segment"}

    def test_emits_drafts_not_articles(self) -> None:
        signature = inspect.signature(ArticleBoundaryStrategy.segment)

        assert signature.return_annotation == "list[ArticleDraft]"

    def test_draft_carries_headline_body_and_page_range(self) -> None:
        assert field_names(ArticleDraft) == ["headline", "body", "page_from", "page_to"]

    def test_strategy_input_includes_publication_for_metadata(self) -> None:
        assert parameter_names(ArticleBoundaryStrategy.segment) == [
            "self",
            "text",
            "publication",
        ]

    def test_strategy_input_is_the_publication_entity(self) -> None:
        assert (
            inspect.signature(ArticleBoundaryStrategy.segment).parameters["publication"].annotation
            == "Publication"
        )


class TestSegmentationVariants:
    def test_single_article_and_clipping_digest_are_distinct_implementations(self) -> None:
        from evidence_corpus.domain.strategies import (
            ClippingDigestStrategy,
            SingleArticleStrategy,
        )

        assert inspect.isclass(SingleArticleStrategy)
        assert inspect.isclass(ClippingDigestStrategy)
        assert SingleArticleStrategy.__name__ != ClippingDigestStrategy.__name__

    def test_digest_variant_emits_one_draft_per_clipping(self) -> None:
        from evidence_corpus.domain.strategies import ClippingDigestStrategy

        digest = (
            "Kassenstellen aufgestockt\nDie Kassenstellen werden aufgestockt.\n"
            "---\n"
            "Spitalsreform beschlossen\nDie Spitalsreform ist beschlossen.\n"
            "---\n"
            "Budget verabschiedet\nDas Budget wurde verabschiedet."
        )

        drafts = ClippingDigestStrategy().segment(digest, None)  # type: ignore[arg-type]

        assert [draft.headline for draft in drafts] == [
            "Kassenstellen aufgestockt",
            "Spitalsreform beschlossen",
            "Budget verabschiedet",
        ]


class TestSegmentArticleUseCase:
    def test_signature_is_frozen(self) -> None:
        assert parameter_names(SegmentArticle.execute) == ["self", "request"]
        assert field_names(SegmentArticleRequest) == ["document_id"]

    def test_result_reports_articles_with_distinct_page_ranges(self) -> None:
        assert field_names(SegmentationResult) == ["document_id", "articles"]

    def test_segmentation_event_records_passage_count(self) -> None:
        assert field_names(ArticleSegmented) == ["document_id", "article_id", "passage_count"]
        assert ArticleSegmented.name == "ArticleSegmented"


class TestSegmentationStrategies:
    def _publication(self) -> Publication:
        from datetime import date

        from evidence_corpus.domain.entities import Publication

        return Publication("Der Standard", date(2026, 10, 1), "print")

    def test_single_article_strategy_uses_first_line_as_headline(self) -> None:
        from evidence_corpus.domain.strategies import SingleArticleStrategy

        text = "Kassenstellen aufgestockt\nDie Kassenstellen werden aufgestockt.\fFortsetzung."

        draft = SingleArticleStrategy().segment(text, self._publication())[0]

        assert draft.headline == "Kassenstellen aufgestockt"
        assert "aufgestockt" in draft.body
        assert (draft.page_from, draft.page_to) == (1, 2)

    def test_clipping_digest_assigns_distinct_page_ranges(self) -> None:
        from evidence_corpus.domain.strategies import ClippingDigestStrategy

        digest = (
            "Erste Meldung\nDie Kassenstellen werden aufgestockt.\n---\n"
            "Zweite Meldung\nDie Spitalsreform ist beschlossen.\n---\n"
            "Dritte Meldung\nDas Budget wurde verabschiedet."
        )

        drafts = ClippingDigestStrategy().segment(digest, self._publication())

        assert len(drafts) == 3
        assert {draft.headline for draft in drafts} == {
            "Erste Meldung",
            "Zweite Meldung",
            "Dritte Meldung",
        }
        assert [draft.page_from for draft in drafts] == [1, 2, 3]
        assert all(draft.page_from == draft.page_to for draft in drafts)

    def test_strategy_is_selected_from_document_markers(self) -> None:
        from evidence_corpus.domain.strategies import (
            ClippingDigestStrategy,
            SingleArticleStrategy,
            select_strategy,
        )

        assert isinstance(select_strategy("Headline\nBody"), SingleArticleStrategy)
        assert isinstance(select_strategy("A\nB\n---\nC\nD"), ClippingDigestStrategy)

    @pytest.mark.parametrize("text", ["", "   ", "\f"])
    def test_empty_documents_cannot_be_segmented(self, text: str) -> None:
        from evidence_corpus.domain.strategies import SingleArticleStrategy

        with pytest.raises(ValueError, match="empty document"):
            SingleArticleStrategy().segment(text, self._publication())


class TestSegmentArticleHandler:
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
            source_uri="s3://corpus/digest.pdf",
            content_hash="sha256:digest",
            publication=Publication("Der Standard", date(2026, 10, 1), "print"),
            source_type=SourceType.PRESS_REPORT,
            language=LanguageTag("de-AT"),
        )
        document.record_extraction(
            "Erste Meldung\nKassenstellen aufgestockt.\n---\n"
            "Zweite Meldung\nSpitalsreform beschlossen.\n---\n"
            "Dritte Meldung\nBudget verabschiedet.",
            ExtractionQuality(ExtractionMethod.NATIVE, 0.98, 0.0),
        )
        document.drain_events()
        return document

    async def test_three_clipping_digest_yields_three_articles(self) -> None:
        from evidence_corpus.application.segmentation_handler import SegmentArticleHandler
        from evidence_corpus.infrastructure.events import RecordingEventPublisher
        from evidence_corpus.infrastructure.memory import InMemoryDocumentRepository

        repository = InMemoryDocumentRepository()
        document = self._document()
        await repository.save(document)
        publisher = RecordingEventPublisher()

        result = await SegmentArticleHandler(repository, publisher).execute(
            SegmentArticleRequest(document_id=document.id)
        )

        assert len(result.articles) == 3
        assert {article.headline for article in result.articles} == {
            "Erste Meldung",
            "Zweite Meldung",
            "Dritte Meldung",
        }
        assert [article.page_from for article in result.articles] == [1, 2, 3]
        from evidence_corpus.domain.events import ArticleSegmented

        assert sum(isinstance(event, ArticleSegmented) for event in publisher.events) == 3

    async def test_unsegmented_document_is_refused(self) -> None:
        from datetime import date

        from evidence_corpus.application.segmentation_handler import SegmentArticleHandler
        from evidence_corpus.domain.entities import Document, Publication
        from evidence_corpus.domain.errors import DocumentNotCitable
        from evidence_corpus.domain.values import LanguageTag, SourceType
        from evidence_corpus.infrastructure.events import RecordingEventPublisher
        from evidence_corpus.infrastructure.memory import InMemoryDocumentRepository

        repository = InMemoryDocumentRepository()
        document = Document.register(
            source_uri="s3://corpus/raw.pdf",
            content_hash="sha256:raw",
            publication=Publication("Der Standard", date(2026, 10, 1), "print"),
            source_type=SourceType.PRESS_REPORT,
            language=LanguageTag("de-AT"),
        )
        await repository.save(document)

        handler = SegmentArticleHandler(repository, RecordingEventPublisher())
        with pytest.raises(DocumentNotCitable):
            await handler.execute(SegmentArticleRequest(document_id=document.id))
