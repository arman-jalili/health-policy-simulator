"""Frozen domain services of EvidenceRetrieval (ADR-008).

Canonical: .pi/architecture/modules/evidence-retrieval.md

CONTRACT FREEZE — service names, layers and signatures are frozen; behaviour is a stub raising
``NotImplementedError`` until the owning implementation issue lands. These services are pure: no
I/O, no ORM, no vendor types.
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import date

from evidence_corpus.domain.published import PassageView
from evidence_corpus.domain.values import SourceType
from evidence_retrieval.domain.ports import StanceModelPort
from evidence_retrieval.domain.values import (
    AuthorityWeight,
    ClaimText,
    EvidenceScore,
    RecencyPolicy,
    StanceLabel,
)


class ScoreEvidenceCandidates:
    """Combine authority, lexical, semantic, recency and directness into an inspectable score."""

    def score(
        self,
        *,
        authority: AuthorityWeight,
        lexical: float,
        semantic: float,
        recency: float,
        directness: float,
    ) -> EvidenceScore:
        """Return the component breakdown whose ``final`` is their sum."""
        raise NotImplementedError("ScoreEvidenceCandidates.score is a frozen stub")


class ApplyRecencyPolicy:
    """Evaluate exponential decay while exempting non-perishable source types."""

    def apply(
        self,
        *,
        policy: RecencyPolicy,
        published_on: date,
        source_type: SourceType,
        as_of: date,
    ) -> float:
        """Return the recency component in ``[0, 1]``; exempt sources keep ``1.0``."""
        raise NotImplementedError("ApplyRecencyPolicy.apply is a frozen stub")


class ReciprocalRankFusion:
    """Fuse lexical and dense rankings into one deterministic ordering (Strategy)."""

    def fuse(
        self,
        rankings: Sequence[Sequence[PassageView]],
        *,
        k: int = 60,
    ) -> list[PassageView]:
        """Return the fused ranking; ``k`` is the RRF smoothing constant."""
        raise NotImplementedError("ReciprocalRankFusion.fuse is a frozen stub")


class StanceClassifier:
    """Classify a passage relative to a claim, validating the model's proposal."""

    def __init__(self, model: StanceModelPort) -> None:
        self._model = model

    async def classify(self, claim: ClaimText, passage: PassageView) -> StanceLabel:
        """Return a validated :class:`StanceLabel` for ``passage`` relative to ``claim``."""
        raise NotImplementedError("StanceClassifier.classify is a frozen stub")
