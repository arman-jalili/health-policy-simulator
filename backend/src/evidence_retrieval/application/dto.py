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
from evidence_corpus.domain.values import SourceType
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
    source_type: SourceType = SourceType.OTHER


@dataclass(frozen=True, slots=True)
class SearchCandidatesResult:
    """Output of ``SearchEvidenceCandidates`` plus the retrieval facts a trace must record."""

    candidates: list[CandidateResult]
    retrieval_mode: str = "lexical"
    embedding_model: str = "none"
    reranker_model: str = "none"
    index_version: str = "unknown"
    query_rewrite: str = ""


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
    retrieval_mode: str = "lexical"
    index_version: str = "unknown"


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
    """Dependency readiness for the active retrieval mode.

    ``mode`` is the capability that actually runs, not an aspiration. An unbound dense/reranker
    port is reported in ``detail`` while the lexical path remains ready.
    """

    embeddings_reachable: bool
    reranker_reachable: bool
    detail: str | None = None
    mode: str = "lexical"
