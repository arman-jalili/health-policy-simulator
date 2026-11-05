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
from evidence_corpus.domain.entities import Article, Document
from evidence_corpus.domain.events import DuplicateArticleLinked
from evidence_corpus.domain.repositories import ArticleRepository
from evidence_corpus.domain.values import CanonicalArticleRef, Offsets, SpeakerKind

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


class TestCanonicalLinking:
    def _document_with_article(self, outlet: str, body: str) -> tuple[Document, Article]:
        from datetime import date

        from evidence_corpus.domain.entities import Document, Publication
        from evidence_corpus.domain.values import (
            ExtractionMethod,
            ExtractionQuality,
            LanguageTag,
            SourceType,
        )

        document = Document.register(
            source_uri=f"s3://corpus/{outlet}.pdf",
            content_hash=f"sha256:{outlet}",
            publication=Publication(outlet, date(2026, 10, 1), "print"),
            source_type=SourceType.PRESS_REPORT,
            language=LanguageTag("de-AT"),
        )
        document.record_extraction(body, ExtractionQuality(ExtractionMethod.NATIVE, 0.99, 0.0))
        article = document.add_article("Kassenstellen", body, 1, 1)
        article.add_passage(
            text=body,
            offsets=Offsets(0, len(body)),
            speaker_kind=SpeakerKind.INSTITUTION,
        )
        document.drain_events()
        return document, article

    async def test_identical_texts_link_to_one_canonical_article(self) -> None:
        from evidence_corpus.application.canonical_handler import LinkCanonicalArticleHandler
        from evidence_corpus.infrastructure.events import RecordingEventPublisher
        from evidence_corpus.infrastructure.memory import (
            InMemoryArticleRepository,
            InMemoryDocumentRepository,
        )

        documents = InMemoryDocumentRepository()
        body = "Die Kassenstellen werden aufgestockt."
        original_doc, original = self._document_with_article("standard", body)
        copy_doc, copy = self._document_with_article("kurier", body)
        await documents.save(original_doc)
        await documents.save(copy_doc)
        publisher = RecordingEventPublisher()

        result = await LinkCanonicalArticleHandler(
            InMemoryArticleRepository(documents), publisher
        ).execute(LinkCanonicalArticleRequest(article_id=copy.id))

        assert result.canonical_article_id == original.id
        assert result.similarity == pytest.approx(1.0)
        assert copy.is_canonical is False
        assert original.is_canonical is True
        from evidence_corpus.domain.events import DuplicateArticleLinked

        assert isinstance(publisher.events[0], DuplicateArticleLinked)

    async def test_duplicate_never_doubles_the_citation_count(self) -> None:
        from evidence_corpus.application.canonical_handler import LinkCanonicalArticleHandler
        from evidence_corpus.infrastructure.events import RecordingEventPublisher
        from evidence_corpus.infrastructure.memory import (
            InMemoryArticleRepository,
            InMemoryDocumentRepository,
        )

        documents = InMemoryDocumentRepository()
        body = "Die Kassenstellen werden aufgestockt."
        original_doc, _original = self._document_with_article("standard", body)
        copy_doc, copy = self._document_with_article("kurier", body)
        await documents.save(original_doc)
        await documents.save(copy_doc)
        articles = InMemoryArticleRepository(documents)

        before = len(original_doc.publishable_passages())
        await LinkCanonicalArticleHandler(articles, RecordingEventPublisher()).execute(
            LinkCanonicalArticleRequest(article_id=copy.id)
        )

        assert copy.publishable_passages() == []
        assert len(original_doc.publishable_passages()) == before

    async def test_unique_text_becomes_its_own_canonical_owner(self) -> None:
        from evidence_corpus.application.canonical_handler import LinkCanonicalArticleHandler
        from evidence_corpus.infrastructure.events import RecordingEventPublisher
        from evidence_corpus.infrastructure.memory import (
            InMemoryArticleRepository,
            InMemoryDocumentRepository,
        )

        documents = InMemoryDocumentRepository()
        document, article = self._document_with_article("standard", "Einzigartiger Text.")
        await documents.save(document)

        result = await LinkCanonicalArticleHandler(
            InMemoryArticleRepository(documents), RecordingEventPublisher()
        ).execute(LinkCanonicalArticleRequest(article_id=article.id))

        assert result.canonical_article_id == article.id
        assert article.is_canonical is True

    async def test_unknown_article_is_not_found(self) -> None:
        from evidence_corpus.application.canonical_handler import LinkCanonicalArticleHandler
        from evidence_corpus.domain.errors import ArticleNotFound
        from evidence_corpus.infrastructure.events import RecordingEventPublisher
        from evidence_corpus.infrastructure.memory import (
            InMemoryArticleRepository,
            InMemoryDocumentRepository,
        )

        documents = InMemoryDocumentRepository()
        handler = LinkCanonicalArticleHandler(
            InMemoryArticleRepository(documents), RecordingEventPublisher()
        )

        with pytest.raises(ArticleNotFound):
            await handler.execute(LinkCanonicalArticleRequest(article_id="art_missing"))
