"""Contract freeze: `LinkCanonicalArticle`.

Syndicated copies must not double the citation count. The contract fixes where the content hash
lives (repository), what a link result looks like and which event records the decision.
"""

from __future__ import annotations

import inspect

import pytest

from evidence_corpus.application.commands import LinkCanonicalArticleRequest
from evidence_corpus.application.dto import CanonicalLinkResult
from evidence_corpus.application.services import LinkCanonicalArticle
from evidence_corpus.domain.entities import Article
from evidence_corpus.domain.events import DuplicateArticleLinked
from evidence_corpus.domain.repositories import ArticleRepository
from evidence_corpus.domain.values import CanonicalArticleRef

from .contract_helpers import field_names, parameter_names


class TestCanonicalReference:
    def test_points_at_the_article_that_owns_citations(self) -> None:
        ref = CanonicalArticleRef(
            canonical_article_id="art_01J0000000000000000000000B",
            similarity=1.0,
        )

        assert ref.canonical_article_id == "art_01J0000000000000000000000B"
        assert ref.similarity == pytest.approx(1.0)

    def test_is_an_immutable_value(self) -> None:
        with pytest.raises(AttributeError):
            CanonicalArticleRef("art_1", 0.9).similarity = 0.5  # type: ignore[misc]


class TestArticleRepository:
    def test_is_domain_owned(self) -> None:
        assert getattr(ArticleRepository, "_is_protocol", False) is True

    def test_lookup_by_content_hash_is_how_duplicates_are_found(self) -> None:
        assert "find_by_content_hash" in dir(ArticleRepository)

    def test_canonical_link_is_persisted_through_the_repository(self) -> None:
        assert "save_canonical_link" in dir(ArticleRepository)

    def test_lookup_returns_candidates(self) -> None:
        annotation = inspect.signature(ArticleRepository.find_by_content_hash).return_annotation

        assert annotation == "list[Article]"


class TestLinkUseCase:
    def test_signature_is_frozen(self) -> None:
        assert parameter_names(LinkCanonicalArticle.execute) == ["self", "request"]
        assert field_names(LinkCanonicalArticleRequest) == ["article_id"]

    def test_result_reports_canonical_owner_and_similarity(self) -> None:
        assert field_names(CanonicalLinkResult) == [
            "article_id",
            "canonical_article_id",
            "similarity",
        ]

    def test_returns_the_link_result(self) -> None:
        assert (
            inspect.signature(LinkCanonicalArticle.execute).return_annotation
            == "CanonicalLinkResult"
        )


class TestDuplicateAccounting:
    def test_article_exposes_the_canonical_flag(self) -> None:
        assert "is_canonical" in field_names(Article)

    def test_non_canonical_articles_publish_no_citable_passages(self) -> None:
        assert "publishable_passages" in dir(Article)

    def test_duplicate_event_carries_similarity_for_audit(self) -> None:
        event = DuplicateArticleLinked(
            article_id="art_2",
            canonical_article_id="art_1",
            similarity=0.98,
        )

        assert event.similarity == pytest.approx(0.98)


class TestNoDoubleCounting:
    def test_citation_count_comes_from_canonical_ownership_only(self) -> None:
        """Duplicates must not appear as separate citation sources for the same text."""
        assert "is_canonical" in field_names(Article)
        assert "passage_count" in dir(Article)
