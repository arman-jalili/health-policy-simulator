"""In-memory repositories for the EvidenceCorpus application layer.

Canonical: .pi/architecture/modules/evidence-corpus.md

Used by the composition root until the SQLAlchemy adapters land, and by the unit tests. They
implement the domain-owned ports exactly, so replacing them with PostgreSQL adapters is a wiring
change, not a domain change.
"""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime

from evidence_corpus.domain.entities import (
    Article,
    CorpusSnapshot,
    Document,
    IndexManifest,
    IngestionRun,
)
from evidence_corpus.domain.published import PassageView
from evidence_corpus.domain.values import AuthorityRule, ClaimType, authority_rule


class InMemoryDocumentRepository:
    def __init__(self) -> None:
        self._documents: dict[str, Document] = {}

    async def get(self, document_id: str) -> Document | None:
        return self._documents.get(document_id)

    async def get_by_hash(self, content_hash: str) -> Document | None:
        return next(
            (doc for doc in self._documents.values() if doc.content_hash == content_hash), None
        )

    async def save(self, document: Document) -> None:
        self._documents[document.id] = document

    async def next_documents(self, limit: int) -> list[str]:
        return sorted(self._documents)[:limit]

    async def list_by_ids(self, document_ids: list[str]) -> list[Document]:
        return [
            self._documents[document_id]
            for document_id in document_ids
            if document_id in self._documents
        ]


class InMemoryArticleRepository:
    def __init__(self, documents: InMemoryDocumentRepository) -> None:
        self._documents = documents
        self._links: list[tuple[str, str, float]] = []

    def _articles(self) -> list[Article]:
        return [article for doc in self._documents._documents.values() for article in doc.articles]

    async def find_by_content_hash(self, content_hash: str) -> list[Article]:
        return [article for article in self._articles() if _article_hash(article) == content_hash]

    async def save_canonical_link(self, article_id: str, canonical: Article) -> None:
        self._links.append((article_id, canonical.id, 1.0))
        for article in self._articles():
            if article.id == canonical.id:
                article.is_canonical = True
            elif article.id == article_id:
                article.is_canonical = False

    async def get(self, article_id: str) -> Article | None:
        return next((a for a in self._articles() if a.id == article_id), None)


def _article_hash(article: Article) -> str:
    normalized = " ".join(article.body.lower().split())
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


class InMemoryPassageRepository:
    def __init__(self, documents: InMemoryDocumentRepository) -> None:
        self._documents = documents

    async def get(self, passage_id: str) -> PassageView | None:
        return next(
            (view for view in await self._all_views() if view.passage_id == passage_id), None
        )

    async def list_by_document(self, document_id: str) -> list[PassageView]:
        return [view for view in await self._all_views() if view.document_id == document_id]

    async def _all_views(self) -> list[PassageView]:
        from evidence_corpus.infrastructure.mapping import passage_view

        return [
            passage_view(document, article, passage)
            for document in self._documents._documents.values()
            for article in document.articles
            for passage in article.passages
        ]


class InMemoryIngestionRunRepository:
    def __init__(self) -> None:
        self._runs: dict[str, IngestionRun] = {}

    async def get(self, run_id: str) -> IngestionRun | None:
        return self._runs.get(run_id)

    async def save(self, run: IngestionRun) -> None:
        self._runs[run.id] = run

    async def latest(self, shard_label: str) -> IngestionRun | None:
        matches = [run for run in self._runs.values() if run.shard_label == shard_label]
        return matches[-1] if matches else None


class InMemoryCorpusSnapshotRepository:
    def __init__(self) -> None:
        self._snapshots: dict[str, CorpusSnapshot] = {}
        self._index_manifest = IndexManifest(
            index_version="idx-0",
            embedding_model="none",
            searchable_since=datetime.now(tz=UTC),
            passage_count=0,
        )

    async def get(self, snapshot_id: str) -> CorpusSnapshot | None:
        return self._snapshots.get(snapshot_id)

    async def save(self, snapshot: CorpusSnapshot) -> None:
        self._snapshots[snapshot.id] = snapshot

    async def list_document_ids(self, snapshot_id: str) -> list[str]:
        snapshot = self._snapshots.get(snapshot_id)
        return list(snapshot.document_ids) if snapshot else []

    async def current_index_manifest(self) -> IndexManifest:
        return self._index_manifest


class InMemoryAuthorityRuleRepository:
    async def for_claim_type(self, claim_type: ClaimType) -> AuthorityRule:
        return authority_rule(claim_type)

    async def list_all(self) -> list[AuthorityRule]:
        return [authority_rule(claim_type) for claim_type in ClaimType]
