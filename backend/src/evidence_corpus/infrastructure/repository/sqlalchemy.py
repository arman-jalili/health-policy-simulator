"""SQLAlchemy adapters for the EvidenceCorpus repository ports.

Canonical: .pi/architecture/modules/evidence-corpus.md

CONTRACT FREEZE — class surfaces exist so the application can be wired; persistence behaviour is a
stub until the persistence issue lands. ORM models and column names stay private to this module
(ADR-002: table ownership is `<context>_<entity>`).
"""

from __future__ import annotations

from evidence_corpus.domain.entities import Article, CorpusSnapshot, Document, IngestionRun
from evidence_corpus.domain.published import PassageView
from evidence_corpus.domain.values import AuthorityRule, ClaimType


class SqlAlchemyDocumentRepository:
    """Adapter for :class:`evidence_corpus.domain.repositories.DocumentRepository`."""

    async def get(self, document_id: str) -> Document | None:
        raise NotImplementedError("SqlAlchemyDocumentRepository.get is a frozen stub")

    async def get_by_hash(self, content_hash: str) -> Document | None:
        raise NotImplementedError("SqlAlchemyDocumentRepository.get_by_hash is a frozen stub")

    async def save(self, document: Document) -> None:
        raise NotImplementedError("SqlAlchemyDocumentRepository.save is a frozen stub")

    async def next_documents(self, limit: int) -> list[str]:
        raise NotImplementedError("SqlAlchemyDocumentRepository.next_documents is a frozen stub")

    async def list_by_ids(self, document_ids: list[str]) -> list[Document]:
        raise NotImplementedError("SqlAlchemyDocumentRepository.list_by_ids is a frozen stub")


class SqlAlchemyArticleRepository:
    """Adapter for :class:`evidence_corpus.domain.repositories.ArticleRepository`."""

    async def find_by_content_hash(self, content_hash: str) -> list[Article]:
        raise NotImplementedError(
            "SqlAlchemyArticleRepository.find_by_content_hash is a frozen stub"
        )

    async def save_canonical_link(self, article_id: str, canonical: Article) -> None:
        raise NotImplementedError(
            "SqlAlchemyArticleRepository.save_canonical_link is a frozen stub"
        )

    async def get(self, article_id: str) -> Article | None:
        raise NotImplementedError("SqlAlchemyArticleRepository.get is a frozen stub")


class SqlAlchemyPassageRepository:
    """Adapter for :class:`evidence_corpus.domain.repositories.PassageRepository`."""

    async def get(self, passage_id: str) -> PassageView | None:
        raise NotImplementedError("SqlAlchemyPassageRepository.get is a frozen stub")

    async def list_by_document(self, document_id: str) -> list[PassageView]:
        raise NotImplementedError("SqlAlchemyPassageRepository.list_by_document is a frozen stub")


class SqlAlchemyIngestionRunRepository:
    """Adapter for :class:`evidence_corpus.domain.repositories.IngestionRunRepository`."""

    async def get(self, run_id: str) -> IngestionRun | None:
        raise NotImplementedError("SqlAlchemyIngestionRunRepository.get is a frozen stub")

    async def save(self, run: IngestionRun) -> None:
        raise NotImplementedError("SqlAlchemyIngestionRunRepository.save is a frozen stub")

    async def latest(self, shard_label: str) -> IngestionRun | None:
        raise NotImplementedError("SqlAlchemyIngestionRunRepository.latest is a frozen stub")


class SqlAlchemyCorpusSnapshotRepository:
    """Adapter for :class:`evidence_corpus.domain.repositories.CorpusSnapshotRepository`."""

    async def get(self, snapshot_id: str) -> CorpusSnapshot | None:
        raise NotImplementedError("SqlAlchemyCorpusSnapshotRepository.get is a frozen stub")

    async def save(self, snapshot: CorpusSnapshot) -> None:
        raise NotImplementedError("SqlAlchemyCorpusSnapshotRepository.save is a frozen stub")

    async def list_document_ids(self, snapshot_id: str) -> list[str]:
        raise NotImplementedError(
            "SqlAlchemyCorpusSnapshotRepository.list_document_ids is a frozen stub"
        )


class SqlAlchemyAuthorityRuleRepository:
    """Adapter for :class:`evidence_corpus.domain.repositories.AuthorityRuleRepository`."""

    async def for_claim_type(self, claim_type: ClaimType) -> AuthorityRule:
        raise NotImplementedError(
            "SqlAlchemyAuthorityRuleRepository.for_claim_type is a frozen stub"
        )

    async def list_all(self) -> list[AuthorityRule]:
        raise NotImplementedError("SqlAlchemyAuthorityRuleRepository.list_all is a frozen stub")
