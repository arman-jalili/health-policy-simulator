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
        """Return the component breakdown whose ``final`` is their sum.

        Inputs are normalized contributions in ``[0, 1]``; authority is the corpus weight. The
        score keeps each contribution visible so a later policy change cannot hide behind a single
        opaque number.
        """
        return EvidenceScore(
            authority=authority.weight,
            lexical=lexical,
            semantic=semantic,
            recency=recency,
            directness=directness,
            final=authority.weight + lexical + semantic + recency + directness,
        )


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
        """Return the fused ranking; ``k`` is the RRF smoothing constant.

        Each ranking contributes ``1 / (k + rank)`` per passage, with rank starting at 1. Ties are
        broken by first appearance across the input rankings, so the result is deterministic.
        """
        if k < 0:
            raise ValueError("ReciprocalRankFusion.k must not be negative")
        scores: dict[str, float] = {}
        first_seen: dict[str, int] = {}
        views: dict[str, PassageView] = {}
        order = 0
        for ranking in rankings:
            for rank, passage in enumerate(ranking, start=1):
                passage_id = passage.passage_id
                scores[passage_id] = scores.get(passage_id, 0.0) + 1.0 / (k + rank)
                if passage_id not in views:
                    views[passage_id] = passage
                    first_seen[passage_id] = order
                    order += 1
        ordered = sorted(
            views,
            key=lambda passage_id: (-scores[passage_id], first_seen[passage_id]),
        )
        return [views[passage_id] for passage_id in ordered]


class StanceClassifier:
    """Classify a passage relative to a claim, validating the model's proposal."""

    def __init__(self, model: StanceModelPort) -> None:
        self._model = model

    async def classify(self, claim: ClaimText, passage: PassageView) -> StanceLabel:
        """Return a validated :class:`StanceLabel` for ``passage`` relative to ``claim``.

        The model proposes; this service refuses anything that is not a declared label. Validation
        happens here so an adapter cannot smuggle sentiment or free text into the stance contract.
        """
        label = await self._model.classify(str(claim), passage)
        if not isinstance(label, StanceLabel):
            raise ValueError(f"stance model returned an unknown label: {label!r}")
        return label
