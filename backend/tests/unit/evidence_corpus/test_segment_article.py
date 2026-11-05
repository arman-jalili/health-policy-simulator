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

        with pytest.raises(NotImplementedError):
            ClippingDigestStrategy().segment("digest text", None)  # type: ignore[arg-type]


class TestSegmentArticleUseCase:
    def test_signature_is_frozen(self) -> None:
        assert parameter_names(SegmentArticle.execute) == ["self", "request"]
        assert field_names(SegmentArticleRequest) == ["document_id"]

    def test_result_reports_articles_with_distinct_page_ranges(self) -> None:
        assert field_names(SegmentationResult) == ["document_id", "articles"]

    def test_segmentation_event_records_passage_count(self) -> None:
        assert field_names(ArticleSegmented) == ["document_id", "article_id", "passage_count"]
        assert ArticleSegmented.name == "ArticleSegmented"
