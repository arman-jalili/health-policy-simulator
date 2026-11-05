"""Frozen domain-event payloads of the EvidenceCorpus bounded context.

Canonical: .pi/architecture/modules/evidence-corpus.md

CONTRACT FREEZE — event names (past tense, immutable facts) and payload fields are the published
contract consumed by other contexts through the transactional outbox (ADR-003). Payloads carry ids
plus the minimum a consumer needs; consumers re-read for detail.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import ClassVar

from evidence_corpus.domain.values import (
    AuthorityTier,
    ExtractionMethod,
    ExtractionQuality,
    SpeakerKind,
)


@dataclass(frozen=True, slots=True)
class DocumentIngested:
    name: ClassVar[str] = "DocumentIngested"
    document_id: str
    source_uri: str
    content_hash: str
    quality_method: ExtractionMethod


@dataclass(frozen=True, slots=True)
class DocumentExtractionFailed:
    name: ClassVar[str] = "DocumentExtractionFailed"
    document_id: str
    method: ExtractionMethod
    reason: str


@dataclass(frozen=True, slots=True)
class DocumentQuarantined:
    name: ClassVar[str] = "DocumentQuarantined"
    document_id: str
    quality: ExtractionQuality
    threshold: float


@dataclass(frozen=True, slots=True)
class ArticleSegmented:
    name: ClassVar[str] = "ArticleSegmented"
    document_id: str
    article_id: str
    passage_count: int


@dataclass(frozen=True, slots=True)
class AuthorityTierAssigned:
    name: ClassVar[str] = "AuthorityTierAssigned"
    document_id: str
    tier: AuthorityTier


@dataclass(frozen=True, slots=True)
class DuplicateArticleLinked:
    name: ClassVar[str] = "DuplicateArticleLinked"
    article_id: str
    canonical_article_id: str
    similarity: float


@dataclass(frozen=True, slots=True)
class QuotationBlockDetected:
    name: ClassVar[str] = "QuotationBlockDetected"
    passage_id: str
    speaker_kind: SpeakerKind


@dataclass(frozen=True, slots=True)
class PersonalQuotationExcluded:
    name: ClassVar[str] = "PersonalQuotationExcluded"
    passage_id: str
    span: tuple[int, int]


@dataclass(frozen=True, slots=True)
class InstitutionalStatementAttributed:
    name: ClassVar[str] = "InstitutionalStatementAttributed"
    passage_id: str
    institution_identity: str


@dataclass(frozen=True, slots=True)
class IngestionRunCompleted:
    name: ClassVar[str] = "IngestionRunCompleted"
    run_id: str
    attempted: int
    accepted: int
    quarantined: int
    failed: int


@dataclass(frozen=True, slots=True)
class IndexManifestPublished:
    name: ClassVar[str] = "IndexManifestPublished"
    snapshot_id: str
    index_version: str
    embedding_model: str
    passage_count: int


@dataclass(frozen=True, slots=True)
class PassageRevertedFromIndex:
    name: ClassVar[str] = "PassageRevertedFromIndex"
    passage_id: str
    reason: str


type DomainEvent = (
    DocumentIngested
    | DocumentExtractionFailed
    | DocumentQuarantined
    | ArticleSegmented
    | AuthorityTierAssigned
    | DuplicateArticleLinked
    | QuotationBlockDetected
    | PersonalQuotationExcluded
    | InstitutionalStatementAttributed
    | IngestionRunCompleted
    | IndexManifestPublished
    | PassageRevertedFromIndex
)
