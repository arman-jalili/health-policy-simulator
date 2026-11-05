"""OpenAPI schemas of the EvidenceRetrieval HTTP interface (ADR-004).

Concrete FastAPI models, not interfaces: they mirror the application DTOs for the wire. Field names
here are the published API contract — renaming one is a breaking change for ``/api/v1``.
"""

from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, Field

from evidence_corpus.domain.values import ClaimType, SourceType
from evidence_retrieval.domain.values import StanceLabel


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


class ScoreBody(BaseModel):
    authority: float
    lexical: float
    semantic: float
    recency: float
    directness: float
    final: float


class CandidateBody(BaseModel):
    passage_id: str
    stance: StanceLabel
    score: ScoreBody
    provenance: ProvenanceBody | None


class SearchCandidatesBody(BaseModel):
    claim: str
    claim_type: ClaimType
    snapshot_id: str
    limit: int = Field(default=20, ge=1, le=100)


class SearchCandidatesResponse(BaseModel):
    candidates: list[CandidateBody]


class AbsenceBody(BaseModel):
    queries: list[str]
    snapshot_id: str
    reason: str


class TraceBody(BaseModel):
    embedding_model: str
    reranker_model: str
    query_rewrite: str
    stance_counts: dict[str, int]
    retrieval_mode: str
    index_version: str


class AssemblePackBody(BaseModel):
    claim: str
    claim_type: ClaimType
    snapshot_id: str


class EvidencePackResponse(BaseModel):
    pack_id: str
    claim: str
    snapshot_id: str
    index_version: str
    candidates: list[CandidateBody]
    absence: AbsenceBody | None
    trace: TraceBody
    frozen_at: datetime


class CandidateScoreBody(BaseModel):
    passage_id: str
    score: ScoreBody


class ScoreBreakdownResponse(BaseModel):
    pack_id: str
    candidates: list[CandidateScoreBody]


class RecencyPolicyBody(BaseModel):
    half_life_days: float = Field(default=365.0, gt=0)
    exempt_source_types: list[SourceType] = Field(default_factory=lambda: [SourceType.LEGISLATION])


class ReweightPackBody(BaseModel):
    policy: RecencyPolicyBody
