"""`LinkCanonicalArticle` use case: one article owns the citations for a text.

Canonical: .pi/architecture/modules/evidence-corpus.md

Duplicates are found by content hash. The canonical owner is the article already marked canonical;
otherwise the older article (lowest id, ULIDs sort by creation time) wins. A non-canonical article
never publishes passages, so citation counts cannot double.
"""

from __future__ import annotations

import hashlib
from difflib import SequenceMatcher

from evidence_corpus.application.commands import LinkCanonicalArticleRequest
from evidence_corpus.application.dto import CanonicalLinkResult
from evidence_corpus.application.events import EventPublisher
from evidence_corpus.domain.errors import ArticleNotFound
from evidence_corpus.domain.events import DuplicateArticleLinked
from evidence_corpus.domain.repositories import ArticleRepository


class LinkCanonicalArticleHandler:
    """Implements :class:`evidence_corpus.application.services.LinkCanonicalArticle`."""

    def __init__(
        self,
        articles: ArticleRepository,
        events: EventPublisher,
        actor: str = "system",
    ) -> None:
        self._articles = articles
        self._events = events
        self._actor = actor

    async def execute(self, request: LinkCanonicalArticleRequest) -> CanonicalLinkResult:
        article = await self._articles.get(request.article_id)
        if article is None:
            raise ArticleNotFound(request.article_id)

        candidates = [
            candidate
            for candidate in await self._articles.find_by_content_hash(content_hash(article.body))
            if candidate.id != article.id
        ]
        if not candidates:
            await self._articles.save_canonical_link(article.id, article)
            return CanonicalLinkResult(
                article_id=article.id,
                canonical_article_id=article.id,
                similarity=1.0,
            )

        canonical = min(
            candidates,
            key=lambda candidate: (not candidate.is_canonical, candidate.id),
        )
        similarity = _similarity(article.body, canonical.body)
        await self._articles.save_canonical_link(article.id, canonical)
        await self._events.publish(
            [
                DuplicateArticleLinked(
                    article_id=article.id,
                    canonical_article_id=canonical.id,
                    similarity=round(similarity, 4),
                )
            ],
            actor=self._actor,
        )
        return CanonicalLinkResult(
            article_id=article.id,
            canonical_article_id=canonical.id,
            similarity=round(similarity, 4),
        )


def content_hash(text: str) -> str:
    normalized = " ".join(text.lower().split())
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def _similarity(left: str, right: str) -> float:
    normalized_left = " ".join(left.lower().split())
    normalized_right = " ".join(right.lower().split())
    return SequenceMatcher(None, normalized_left, normalized_right).ratio()
