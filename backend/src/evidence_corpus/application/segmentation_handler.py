"""`SegmentArticle` use case: derive boundaries and let the aggregate own the articles.

Canonical: .pi/architecture/modules/evidence-corpus.md
"""

from __future__ import annotations

from evidence_corpus.application.commands import SegmentArticleRequest
from evidence_corpus.application.dto import ArticleView, SegmentationResult
from evidence_corpus.application.events import EventPublisher
from evidence_corpus.domain.entities import Article
from evidence_corpus.domain.errors import DocumentNotCitable, DocumentNotFound
from evidence_corpus.domain.repositories import DocumentRepository
from evidence_corpus.domain.services import ArticleBoundaryStrategy
from evidence_corpus.domain.strategies import select_strategy
from evidence_corpus.domain.values import Offsets, SpeakerKind


class SegmentArticleHandler:
    """Implements :class:`evidence_corpus.application.services.SegmentArticle`."""

    def __init__(
        self,
        documents: DocumentRepository,
        events: EventPublisher,
        strategy: ArticleBoundaryStrategy | None = None,
        actor: str = "system",
    ) -> None:
        self._documents = documents
        self._events = events
        self._strategy = strategy
        self._actor = actor

    async def execute(self, request: SegmentArticleRequest) -> SegmentationResult:
        document = await self._documents.get(request.document_id)
        if document is None:
            raise DocumentNotFound(request.document_id)
        if not document.is_citable() or document.extracted_text is None:
            raise DocumentNotCitable(document.id)

        strategy = self._strategy or select_strategy(document.extracted_text)
        drafts = strategy.segment(document.extracted_text, document.publication)
        articles = []
        for draft in drafts:
            article = document.add_article(
                draft.headline, draft.body, draft.page_from, draft.page_to
            )
            # Segmentation owns the article boundaries; publish one citable body span now so the
            # indexer has real passages to search. Finer sentence/quote splitting can replace this
            # without changing the API pipeline.
            article.add_passage(
                text=draft.body,
                offsets=Offsets(0, len(draft.body)),
                speaker_kind=SpeakerKind.INSTITUTION,
            )
            articles.append(article)

        await self._documents.save(document)
        await self._events.publish(document.drain_events(), actor=self._actor)
        return SegmentationResult(
            document_id=document.id,
            articles=[_article_view(article) for article in articles],
        )


def _article_view(article: Article) -> ArticleView:
    return ArticleView(
        article_id=article.id,
        headline=article.headline,
        page_from=article.page_from,
        page_to=article.page_to,
        is_canonical=article.is_canonical,
        passage_count=article.passage_count(),
    )
