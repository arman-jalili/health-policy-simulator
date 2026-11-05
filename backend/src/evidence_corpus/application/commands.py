"""Application-layer request DTOs (commands and queries) of EvidenceCorpus.

Canonical: .pi/architecture/modules/evidence-corpus.md

Frozen interface: one request object per use case, so adding a parameter never changes a service
signature that callers already implement. Framework-free on purpose.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from evidence_corpus.domain.values import ClaimType, SourceType


@dataclass(frozen=True, slots=True)
class PublicationInput:
    """Publication as supplied by the operator at ingestion."""

    outlet: str
    published_on: date
    medium: str


@dataclass(frozen=True, slots=True)
class IngestDocumentRequest:
    """Register and extract one source file."""

    source_uri: str
    publication: PublicationInput
    source_type: SourceType


@dataclass(frozen=True, slots=True)
class StartIngestionRunRequest:
    """Start one auditable batch over a shard of source paths."""

    shard_label: str
    paths: list[str]


@dataclass(frozen=True, slots=True)
class ExtractDocumentTextRequest:
    document_id: str


@dataclass(frozen=True, slots=True)
class SegmentArticleRequest:
    document_id: str


@dataclass(frozen=True, slots=True)
class ClassifySourceAuthorityRequest:
    document_id: str


@dataclass(frozen=True, slots=True)
class LinkCanonicalArticleRequest:
    article_id: str


@dataclass(frozen=True, slots=True)
class PinCorpusSnapshotRequest:
    """Pin the manifest a run may search; `document_ids=None` means "everything indexed"."""

    label: str
    document_ids: list[str] | None = None


@dataclass(frozen=True, slots=True)
class IndexIngestedPassagesRequest:
    document_id: str


@dataclass(frozen=True, slots=True)
class ResolvePassageRequest:
    passage_id: str


@dataclass(frozen=True, slots=True)
class GetDocumentRequest:
    document_id: str


@dataclass(frozen=True, slots=True)
class GetIngestionRunRequest:
    run_id: str


@dataclass(frozen=True, slots=True)
class GetCorpusSnapshotRequest:
    snapshot_id: str


@dataclass(frozen=True, slots=True)
class ListAuthorityRulesRequest:
    """`claim_type=None` returns every rule; otherwise the rule for that claim type."""

    claim_type: ClaimType | None = None
