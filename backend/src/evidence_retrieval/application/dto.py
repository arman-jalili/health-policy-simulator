"""Application-layer result DTOs of EvidenceRetrieval.

Canonical: .pi/architecture/modules/evidence-retrieval.md

Frozen interface: these are the shapes the HTTP layer and the ACL serialise. Framework-free; the
pydantic schemas in ``interfaces/http/schemas.py`` mirror them. Published views in
``interfaces/published.py`` deliberately drop vectors before NegotiationSession sees them.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime

from evidence_corpus.domain.published import ProvenanceView
from evidence_retrieval.domain.values import (
    EvidenceScore,
    PassageId,
    StanceLabel,
)


@dataclass(frozen=True, slots=True)
class CandidateResult:
    """One retrieved passage as the application layer returns it."""

    passage_id: PassageId
    stance: StanceLabel
    score: EvidenceScore
    provenance: ProvenanceView | None


@dataclass(frozen=True, slots=True)
class SearchCandidatesResult:
    """Output of ``SearchEvidenceCandidates``."""

    candidates: list[CandidateResult]


@dataclass(frozen=True, slots=True)
class AbsenceResult:
    """Application DTO for a truthful negative result."""

    queries: list[str]
    snapshot_id: str
    reason: str


@dataclass(frozen=True, slots=True)
class TraceResult:
    """Reproducibility data attached to a pack result."""

    embedding_model: str
    reranker_model: str
    query_rewrite: str
    stance_counts: Mapping[StanceLabel, int]


@dataclass(frozen=True, slots=True)
class EvidencePackResult:
    """Output of ``AssembleEvidencePack`` and reads of a stored pack."""

    pack_id: str
    claim: str
    snapshot_id: str
    index_version: str
    candidates: list[CandidateResult]
    absence: AbsenceResult | None
    trace: TraceResult
    frozen_at: datetime


@dataclass(frozen=True, slots=True)
class CandidateScoreResult:
    """Per-candidate breakdown returned by the score endpoint."""

    passage_id: PassageId
    score: EvidenceScore


@dataclass(frozen=True, slots=True)
class ScoreBreakdownResult:
    """Output of ``GetScoreBreakdown``."""

    pack_id: str
    candidates: list[CandidateScoreResult]


@dataclass(frozen=True, slots=True)
class RetrievalReadiness:
    """Dependency readiness for hybrid retrieval; readiness must be red if either is unreachable."""

    embeddings_reachable: bool
    reranker_reachable: bool
    detail: str | None = None
