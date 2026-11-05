"""Application service interfaces (use-case orchestration) of EvidenceCorpus.

Canonical: .pi/architecture/modules/evidence-corpus.md

CONTRACT FREEZE — interfaces only: one `execute(request)` per use case, request/response DTOs from
`commands.py` and `dto.py`. Implementations live in the owning issues and must not add business
rules here (ADR-008: application services are thin).
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from evidence_corpus.application.commands import (
    ClassifySourceAuthorityRequest,
    ExtractDocumentTextRequest,
    GetCorpusSnapshotRequest,
    GetDocumentRequest,
    GetIngestionRunRequest,
    IndexIngestedPassagesRequest,
    IngestDocumentRequest,
    LinkCanonicalArticleRequest,
    ListAuthorityRulesRequest,
    PinCorpusSnapshotRequest,
    ResolvePassageRequest,
    SegmentArticleRequest,
    StartIngestionRunRequest,
)
from evidence_corpus.application.dto import (
    AuthorityRuleView,
    CanonicalLinkResult,
    ClassifyAuthorityResult,
    DocumentIngestionResult,
    DocumentView,
    ExtractionOutcome,
    IndexManifestView,
    IngestionRunView,
    SegmentationResult,
    SnapshotView,
)
from evidence_corpus.domain.published import PassageView


@runtime_checkable
class IngestDocument(Protocol):
    """Register a source file, extract it, apply the quality gate and emit events."""

    async def execute(self, request: IngestDocumentRequest) -> DocumentIngestionResult: ...


@runtime_checkable
class ExtractDocumentText(Protocol):
    """Route native vs OCR extraction and record the measured quality."""

    async def execute(self, request: ExtractDocumentTextRequest) -> ExtractionOutcome: ...


@runtime_checkable
class SegmentArticle(Protocol):
    """Segment a document into articles using the configured boundary strategy."""

    async def execute(self, request: SegmentArticleRequest) -> SegmentationResult: ...


@runtime_checkable
class ClassifySourceAuthority(Protocol):
    """Assign the authority tier for the document's source type and detect duplicates."""

    async def execute(self, request: ClassifySourceAuthorityRequest) -> ClassifyAuthorityResult: ...


@runtime_checkable
class LinkCanonicalArticle(Protocol):
    """Link a syndicated copy to the article that owns citations."""

    async def execute(self, request: LinkCanonicalArticleRequest) -> CanonicalLinkResult: ...


@runtime_checkable
class PinCorpusSnapshot(Protocol):
    """Pin the document set plus index version a run may search."""

    async def execute(self, request: PinCorpusSnapshotRequest) -> SnapshotView: ...


@runtime_checkable
class IndexIngestedPassages(Protocol):
    """Write searchable passages (tsvector + embeddings) for a document; idempotent."""

    async def execute(self, request: IndexIngestedPassagesRequest) -> IndexManifestView: ...


@runtime_checkable
class ResolvePassage(Protocol):
    """Resolve a citation: passage text plus provenance that reproduces the source slice."""

    async def execute(self, request: ResolvePassageRequest) -> PassageView: ...


@runtime_checkable
class GetDocument(Protocol):
    """Read a document with its articles."""

    async def execute(self, request: GetDocumentRequest) -> DocumentView: ...


@runtime_checkable
class StartIngestionRun(Protocol):
    """Open an auditable batch over a shard of source paths."""

    async def execute(self, request: StartIngestionRunRequest) -> IngestionRunView: ...


@runtime_checkable
class GetIngestionRun(Protocol):
    """Read batch progress and outcome counts."""

    async def execute(self, request: GetIngestionRunRequest) -> IngestionRunView: ...


@runtime_checkable
class GetCorpusSnapshot(Protocol):
    """Read a snapshot manifest and the index version it resolves to."""

    async def execute(self, request: GetCorpusSnapshotRequest) -> SnapshotView: ...


@runtime_checkable
class ListAuthorityRules(Protocol):
    """List the frozen authority rubric, optionally for one claim type."""

    async def execute(self, request: ListAuthorityRulesRequest) -> list[AuthorityRuleView]: ...
