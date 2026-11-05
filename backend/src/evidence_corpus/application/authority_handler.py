"""`ClassifySourceAuthority` use case: claim-type-relative tier plus duplicate detection.

Canonical: .pi/architecture/modules/evidence-corpus.md

Authority is a rubric position, not a heuristic: the declared source type selects the tier, the
aggregate freezes it, and an unknown source type is refused (invariants 6 and 7). Duplicate
detection only reports candidate articles; linking them to a canonical owner is a separate use case
so the citation count stays single-sourced.
"""

from __future__ import annotations

import hashlib

from evidence_corpus.application.commands import ClassifySourceAuthorityRequest
from evidence_corpus.application.dto import ClassifyAuthorityResult
from evidence_corpus.application.events import EventPublisher
from evidence_corpus.domain.entities import Document
from evidence_corpus.domain.errors import (
    AuthorityAlreadyAssigned,
    DocumentNotFound,
    SourceTypeUnknown,
)
from evidence_corpus.domain.repositories import ArticleRepository, DocumentRepository
from evidence_corpus.domain.values import AuthorityTier, SourceType


class ClassifySourceAuthorityHandler:
    """Implements :class:`evidence_corpus.application.services.ClassifySourceAuthority`."""

    def __init__(
        self,
        documents: DocumentRepository,
        articles: ArticleRepository,
        events: EventPublisher,
        actor: str = "system",
    ) -> None:
        self._documents = documents
        self._articles = articles
        self._events = events
        self._actor = actor

    async def execute(self, request: ClassifySourceAuthorityRequest) -> ClassifyAuthorityResult:
        document = await self._documents.get(request.document_id)
        if document is None:
            raise DocumentNotFound(request.document_id)
        if document.source_type is SourceType.UNKNOWN:
            raise SourceTypeUnknown(document.id)
        if document.tier is not None:
            raise AuthorityAlreadyAssigned(document.id)

        duplicates = await self._duplicate_article_ids(document)
        document.classify(AuthorityTier(document.source_type.value))

        await self._documents.save(document)
        await self._events.publish(document.drain_events(), actor=self._actor)
        return ClassifyAuthorityResult(
            document_id=document.id,
            tier=document.tier,
            duplicate_article_ids=duplicates,
        )

    async def _duplicate_article_ids(self, document: Document) -> list[str]:
        own_hashes = {_content_hash(article.body) for article in document.articles}
        duplicates: list[str] = []
        for article in document.articles:
            if _content_hash(article.body) not in own_hashes:
                continue
        for digest in sorted(own_hashes):
            for candidate in await self._articles.find_by_content_hash(digest):
                if candidate.document_id != document.id:
                    duplicates.append(candidate.id)
        return sorted(set(duplicates))


def _content_hash(text: str) -> str:
    normalized = " ".join(text.lower().split())
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()
