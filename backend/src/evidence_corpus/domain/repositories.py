"""Domain-owned repository interfaces for EvidenceCorpus (ADR-001, ADR-008).

Canonical: .pi/architecture/modules/evidence-corpus.md

The domain declares what it needs; infrastructure adapters (`infrastructure/repository/`)
provide it.
No code outside this module may import ORM types into the domain.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from evidence_corpus.domain.entities import (
    Article,
    CorpusSnapshot,
    Document,
    IndexManifest,
    IngestionRun,
)
from evidence_corpus.domain.published import PassageView
from evidence_corpus.domain.values import AuthorityRule, ClaimType


@runtime_checkable
class DocumentRepository(Protocol):
    """Persistence port for the Document aggregate (one aggregate per transaction)."""

    async def get(self, document_id: str) -> Document | None: ...

    async def get_by_hash(self, content_hash: str) -> Document | None: ...

    async def save(self, document: Document) -> None: ...

    async def next_documents(self, limit: int) -> list[str]: ...

    async def list_by_ids(self, document_ids: list[str]) -> list[Document]: ...


@runtime_checkable
class ArticleRepository(Protocol):
    """Persistence port for Article identity, duplicates and canonical ownership."""

    async def find_by_content_hash(self, content_hash: str) -> list[Article]: ...

    async def save_canonical_link(self, article_id: str, canonical: Article) -> None: ...

    async def get(self, article_id: str) -> Article | None: ...


@runtime_checkable
class PassageRepository(Protocol):
    """Read port for citation resolution; writes go through the Document aggregate."""

    async def get(self, passage_id: str) -> PassageView | None: ...

    async def list_by_document(self, document_id: str) -> list[PassageView]: ...


@runtime_checkable
class IngestionRunRepository(Protocol):
    """Persistence port for the IngestionRun aggregate."""

    async def get(self, run_id: str) -> IngestionRun | None: ...

    async def save(self, run: IngestionRun) -> None: ...

    async def latest(self, shard_label: str) -> IngestionRun | None: ...


@runtime_checkable
class CorpusSnapshotRepository(Protocol):
    """Persistence port for snapshot manifests (never for corpus-wide transactions)."""

    async def get(self, snapshot_id: str) -> CorpusSnapshot | None: ...

    async def get_by_label(self, label: str) -> CorpusSnapshot | None: ...

    async def latest(self) -> CorpusSnapshot | None: ...

    async def save(self, snapshot: CorpusSnapshot) -> None: ...

    async def list_document_ids(self, snapshot_id: str) -> list[str]: ...

    async def current_index_manifest(self) -> IndexManifest: ...


@runtime_checkable
class AuthorityRuleRepository(Protocol):
    """Read port for the corpus-owned authority rubric."""

    async def for_claim_type(self, claim_type: ClaimType) -> AuthorityRule: ...

    async def list_all(self) -> list[AuthorityRule]: ...
