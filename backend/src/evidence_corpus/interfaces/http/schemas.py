"""OpenAPI schemas of the EvidenceCorpus HTTP interface (ADR-004).

Concrete FastAPI models, not interfaces: they mirror the application DTOs for the wire. Field names
here are the published API contract — renaming one is a breaking change for `/api/v1`.
"""

from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, Field

from evidence_corpus.domain.values import (
    ArticleSection,
    AuthorityTier,
    ClaimType,
    ExtractionMethod,
    LanguageTag,
    SourceType,
    SpeakerKind,
)


class PublicationBody(BaseModel):
    outlet: str
    published_on: date
    medium: str


class IngestDocumentBody(BaseModel):
    source_uri: str = Field(description="Object-store URI of the source file")
    publication: PublicationBody
    source_type: SourceType = Field(
        description="Declared source type; 'unknown' is refused by ClassifySourceAuthority"
    )


class ExtractionQualityBody(BaseModel):
    method: ExtractionMethod
    confidence: float
    missing_glyph_rate: float
    page_count: int


class DocumentIngestionBody(BaseModel):
    document_id: str
    quality: ExtractionQualityBody
    citable: bool


class StartIngestionRunBody(BaseModel):
    shard_label: str
    paths: list[str]


class StartIngestionRunResponse(BaseModel):
    run_id: str
    status: str


class IngestionRunResponse(BaseModel):
    run_id: str
    shard_label: str
    status: str
    attempted: int
    accepted: int
    quarantined: int
    failed: int


class OffsetsBody(BaseModel):
    start: int
    end: int


class ProvenanceBody(BaseModel):
    outlet: str
    published_on: date
    medium: str
    page_from: int
    page_to: int
    offsets: OffsetsBody
    source_uri: str


class ArticleResponse(BaseModel):
    article_id: str
    headline: str
    page_from: int
    page_to: int
    is_canonical: bool
    passage_count: int


class DocumentResponse(BaseModel):
    document_id: str
    source_uri: str
    content_hash: str
    publication: PublicationBody
    source_type: SourceType
    language: LanguageTag
    tier: AuthorityTier | None
    quality: ExtractionQualityBody | None
    citable: bool
    articles: list[ArticleResponse]


class PassageResponse(BaseModel):
    passage_id: str
    text: str
    provenance: ProvenanceBody
    speaker_kind: SpeakerKind
    citable: bool
    section: ArticleSection


class PinSnapshotBody(BaseModel):
    label: str
    document_ids: list[str] | None = Field(
        default=None, description="Explicit document set; omit to pin everything indexed"
    )


class IndexManifestBody(BaseModel):
    index_version: str
    embedding_model: str
    searchable_since: datetime
    passage_count: int


class PinSnapshotResponse(BaseModel):
    snapshot_id: str
    manifest_hash: str


class SnapshotResponse(BaseModel):
    snapshot_id: str
    label: str
    manifest_hash: str
    pinned_at: datetime
    document_ids: list[str]
    index: IndexManifestBody


class AuthorityRuleResponse(BaseModel):
    claim_type: ClaimType
    ordered_tiers: list[AuthorityTier]
