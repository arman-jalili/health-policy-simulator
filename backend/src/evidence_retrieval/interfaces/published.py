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
from evidence_retrieval.application.dto import EvidencePackResult, ScoreBreakdownResult
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
    retrieval_mode: str
    index_version: str


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


@dataclass(frozen=True, slots=True)
class ClaimEvidenceRef:
    """The only shape NegotiationSession receives: a passage reference, never raw hits."""

    passage_id: str
    stance: StanceLabel
    provenance: ProvenanceView | None


def to_published_pack(result: EvidencePackResult) -> EvidencePackView:
    """Map an application result to the vector-free published language."""
    return EvidencePackView(
        pack_id=result.pack_id,
        claim=result.claim,
        snapshot_id=result.snapshot_id,
        index_version=result.index_version,
        candidates=[
            EvidenceCandidateView(
                passage_id=candidate.passage_id,
                stance=candidate.stance,
                score=ScoreView(
                    authority=candidate.score.authority,
                    lexical=candidate.score.lexical,
                    semantic=candidate.score.semantic,
                    recency=candidate.score.recency,
                    directness=candidate.score.directness,
                    final=candidate.score.final,
                ),
                provenance=candidate.provenance,
            )
            for candidate in result.candidates
        ],
        absence=(
            AbsenceView(
                queries=result.absence.queries,
                snapshot_id=result.absence.snapshot_id,
                reason=result.absence.reason,
            )
            if result.absence is not None
            else None
        ),
        trace=RetrievalTraceView(
            embedding_model=result.trace.embedding_model,
            reranker_model=result.trace.reranker_model,
            query_rewrite=result.trace.query_rewrite,
            stance_counts=result.trace.stance_counts,
            retrieval_mode=result.trace.retrieval_mode,
            index_version=result.trace.index_version,
        ),
        frozen_at=result.frozen_at,
    )


def to_claim_evidence_refs(view: EvidencePackView) -> list[ClaimEvidenceRef]:
    """Drop scores and text for the downstream ACL; keep the resolvable reference."""
    return [
        ClaimEvidenceRef(
            passage_id=candidate.passage_id,
            stance=candidate.stance,
            provenance=candidate.provenance,
        )
        for candidate in view.candidates
    ]


def to_published_breakdown(result: ScoreBreakdownResult) -> ScoreBreakdownView:
    """Map a score result without exposing vectors or ORM rows."""
    return ScoreBreakdownView(
        pack_id=result.pack_id,
        candidates=[
            CandidateScoreView(
                passage_id=candidate.passage_id,
                score=ScoreView(
                    authority=candidate.score.authority,
                    lexical=candidate.score.lexical,
                    semantic=candidate.score.semantic,
                    recency=candidate.score.recency,
                    directness=candidate.score.directness,
                    final=candidate.score.final,
                ),
            )
            for candidate in result.candidates
        ],
    )
