"""Read use cases of EvidenceCorpus: citation resolution and document inspection.

Canonical: .pi/architecture/modules/evidence-corpus.md

Reads never mutate the aggregate; they map persisted aggregate state onto the published language
(`PassageView`, `DocumentView`) so consumers never see repository rows.
"""

from __future__ import annotations

from evidence_corpus.application.commands import GetDocumentRequest, ResolvePassageRequest
from evidence_corpus.application.dto import ArticleView, DocumentView, PublicationView
from evidence_corpus.domain.entities import Article, Document
from evidence_corpus.domain.errors import DocumentNotFound, PassageNotFound
from evidence_corpus.domain.published import PassageView
from evidence_corpus.domain.repositories import DocumentRepository, PassageRepository


class ResolvePassageHandler:
    """Implements :class:`evidence_corpus.application.services.ResolvePassage`."""

    def __init__(self, passages: PassageRepository) -> None:
        self._passages = passages

    async def execute(self, request: ResolvePassageRequest) -> PassageView:
        view = await self._passages.get(request.passage_id)
        if view is None:
            raise PassageNotFound(request.passage_id)
        return view


class GetDocumentHandler:
    """Implements :class:`evidence_corpus.application.services.GetDocument`."""

    def __init__(self, documents: DocumentRepository) -> None:
        self._documents = documents

    async def execute(self, request: GetDocumentRequest) -> DocumentView:
        document = await self._documents.get(request.document_id)
        if document is None:
            raise DocumentNotFound(request.document_id)
        return document_view(document)


def document_view(document: Document) -> DocumentView:
    return DocumentView(
        document_id=document.id,
        source_uri=document.source_uri,
        content_hash=document.content_hash,
        publication=PublicationView(
            outlet=document.publication.outlet,
            published_on=document.publication.published_on,
            medium=document.publication.medium,
        ),
        source_type=document.source_type,
        language=document.language,
        tier=document.tier,
        quality=document.quality,
        citable=bool(document.publishable_passages()),
        articles=[article_view(article) for article in document.articles],
    )


def article_view(article: Article) -> ArticleView:
    return ArticleView(
        article_id=article.id,
        headline=article.headline,
        page_from=article.page_from,
        page_to=article.page_to,
        is_canonical=article.is_canonical,
        passage_count=article.passage_count(),
    )
