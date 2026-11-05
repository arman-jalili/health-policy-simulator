"""Application-layer response DTOs of EvidenceCorpus.

Canonical: .pi/architecture/modules/evidence-corpus.md

Frozen interface: these are the shapes the HTTP layer serialises and other contexts may read.
Framework-free; the FastAPI schemas in `interfaces/http/schemas.py` mirror them.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime

from evidence_corpus.domain.values import (
    AuthorityTier,
    ClaimType,
    ExtractionQuality,
    LanguageTag,
    SourceType,
)


@dataclass(frozen=True, slots=True)
class PublicationView:
    outlet: str
    published_on: date
    medium: str


@dataclass(frozen=True, slots=True)
class ExtractionOutcome:
    """Result of `ExtractDocumentText`: text plus the measured route and fidelity."""

    document_id: str
    text: str
    quality: ExtractionQuality


@dataclass(frozen=True, slots=True)
class DocumentIngestionResult:
    """202 payload of `POST /corpus/documents`."""

    document_id: str
    quality: ExtractionQuality
    citable: bool


@dataclass(frozen=True, slots=True)
class ArticleView:
    article_id: str
    headline: str
    page_from: int
    page_to: int
    is_canonical: bool
    passage_count: int


@dataclass(frozen=True, slots=True)
class SegmentationResult:
    document_id: str
    articles: list[ArticleView]


@dataclass(frozen=True, slots=True)
class ClassifyAuthorityResult:
    """Assigned tier plus duplicate articles detected for later canonical linking."""

    document_id: str
    tier: AuthorityTier | None
    duplicate_article_ids: list[str]


@dataclass(frozen=True, slots=True)
class CanonicalLinkResult:
    """Which article owns citations for this text, and how similar the match was."""

    article_id: str
    canonical_article_id: str
    similarity: float


@dataclass(frozen=True, slots=True)
class DocumentView:
    """Document plus articles, as returned by `GET /documents/{id}`."""

    document_id: str
    source_uri: str
    content_hash: str
    publication: PublicationView
    source_type: SourceType
    language: LanguageTag
    tier: AuthorityTier | None
    quality: ExtractionQuality | None
    citable: bool
    articles: list[ArticleView]


@dataclass(frozen=True, slots=True)
class IngestionRunView:
    """Outcome counts and lifecycle of one batch execution."""

    run_id: str
    shard_label: str
    status: str
    attempted: int
    accepted: int
    quarantined: int
    failed: int


@dataclass(frozen=True, slots=True)
class IndexManifestView:
    """Published index state of a snapshot; consumers must quote this when citing."""

    index_version: str
    embedding_model: str
    searchable_since: datetime
    passage_count: int


@dataclass(frozen=True, slots=True)
class SnapshotView:
    """Manifest a run may search: document set plus the index version it resolves to."""

    snapshot_id: str
    label: str
    manifest_hash: str
    pinned_at: datetime
    document_ids: list[str]
    index: IndexManifestView


@dataclass(frozen=True, slots=True)
class AuthorityRuleView:
    """Claim-type-specific tier ordering, ordered most authoritative first."""

    claim_type: ClaimType
    ordered_tiers: list[AuthorityTier]
