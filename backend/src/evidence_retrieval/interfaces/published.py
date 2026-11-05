"""Published views of EvidenceRetrieval for downstream contexts (ADR-003, ACL).

Canonical: .pi/architecture/modules/evidence-retrieval.md

These are the only shapes that cross into NegotiationSession/ClaimValidation/DecisionBrief. They
contain references and provenance, never raw embedding vectors or corpus rows. The ACL maps them to
``ClaimEvidence`` refs downstream.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime

from evidence_corpus.domain.published import ProvenanceView
from evidence_retrieval.domain.values import StanceLabel


@dataclass(frozen=True, slots=True)
class ScoreView:
    """Inspectable component weights; ``final`` is their sum."""

    authority: float
    lexical: float
    semantic: float
    recency: float
    directness: float
    final: float


@dataclass(frozen=True, slots=True)
class EvidenceCandidateView:
    """A passage reference with stance, score and provenance — no passage text or vector."""

    passage_id: str
    stance: StanceLabel
    score: ScoreView
    provenance: ProvenanceView | None


@dataclass(frozen=True, slots=True)
class AbsenceView:
    """Truthful negative result with the searches that produced it."""

    queries: list[str]
    snapshot_id: str
    reason: str


@dataclass(frozen=True, slots=True)
class RetrievalTraceView:
    """Reproducibility record; model names are strings, never vectors."""

    embedding_model: str
    reranker_model: str
    query_rewrite: str
    stance_counts: Mapping[StanceLabel, int]


@dataclass(frozen=True, slots=True)
class EvidencePackView:
    """Frozen pack as published to other contexts."""

    pack_id: str
    claim: str
    snapshot_id: str
    index_version: str
    candidates: list[EvidenceCandidateView]
    absence: AbsenceView | None
    trace: RetrievalTraceView
    frozen_at: datetime


@dataclass(frozen=True, slots=True)
class CandidateScoreView:
    """One candidate's breakdown for inspection."""

    passage_id: str
    score: ScoreView


@dataclass(frozen=True, slots=True)
class ScoreBreakdownView:
    """Per-candidate weights published for audit and UI."""

    pack_id: str
    candidates: list[CandidateScoreView]
