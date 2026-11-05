"""`IndexIngestedPassages` use case: publish citable passages for search.

Canonical: .pi/architecture/modules/evidence-corpus.md
"""

from __future__ import annotations

from evidence_corpus.application.commands import IndexIngestedPassagesRequest
from evidence_corpus.application.dto import IndexManifestView
from evidence_corpus.application.events import EventPublisher
from evidence_corpus.application.ports import IndexWriterPort
from evidence_corpus.domain.entities import Document
from evidence_corpus.domain.errors import DocumentNotCitable, DocumentNotFound
from evidence_corpus.domain.events import IndexManifestPublished
from evidence_corpus.domain.published import PassageView
from evidence_corpus.domain.repositories import DocumentRepository
from evidence_corpus.infrastructure.mapping import passage_view


class IndexIngestedPassagesHandler:
    """Implements :class:`evidence_corpus.application.services.IndexIngestedPassages`."""

    def __init__(
        self,
        documents: DocumentRepository,
        writer: IndexWriterPort,
        events: EventPublisher,
        actor: str = "system",
    ) -> None:
        self._documents = documents
        self._writer = writer
        self._events = events
        self._actor = actor

    async def execute(self, request: IndexIngestedPassagesRequest) -> IndexManifestView:
        document = await self._documents.get(request.document_id)
        if document is None:
            raise DocumentNotFound(request.document_id)
        if not document.is_citable():
            raise DocumentNotCitable(document.id)

        manifest = await self._writer.upsert_passages(document.id, _passage_views(document))
        await self._events.publish(
            [
                IndexManifestPublished(
                    snapshot_id=document.id,
                    index_version=manifest.index_version,
                    embedding_model=manifest.embedding_model,
                    passage_count=manifest.passage_count,
                )
            ],
            actor=self._actor,
        )
        return manifest


def _passage_views(document: Document) -> list[PassageView]:
    return [
        passage_view(document, article, passage)
        for article in document.articles
        for passage in article.publishable_passages()
    ]
