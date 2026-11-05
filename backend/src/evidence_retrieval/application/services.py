"""Frozen application services of EvidenceRetrieval.

Canonical: .pi/architecture/modules/evidence-retrieval.md

CONTRACT FREEZE — constructors, service names and ``execute`` signatures are frozen; behaviour is
a stub raising ``NotImplementedError`` until the owning implementation issue lands.
"""

from __future__ import annotations

from evidence_corpus.domain.values import AuthorityTier
from evidence_retrieval.application.commands import (
    ApplyRecencyPolicyRequest,
    AssembleEvidencePackRequest,
    GetEvidencePackRequest,
    GetScoreBreakdownRequest,
    SearchEvidenceCandidatesRequest,
)
from evidence_retrieval.application.dto import (
    CandidateResult,
    EvidencePackResult,
    ScoreBreakdownResult,
    SearchCandidatesResult,
)
from evidence_retrieval.application.ports import Clock, QueryRewritePort
from evidence_retrieval.domain.repositories import EvidencePackRepository, PassageSearchPort
from evidence_retrieval.domain.services import (
    ApplyRecencyPolicy,
    ReciprocalRankFusion,
    ScoreEvidenceCandidates,
    StanceClassifier,
)
from evidence_retrieval.domain.values import (
    AuthorityWeight,
    ClaimText,
    PassageId,
    SnapshotId,
)


class SearchEvidenceCandidates:
    """Orchestrate query rewrite, corpus search, fusion and stance classification."""

    def __init__(
        self,
        *,
        search_port: PassageSearchPort,
        query_rewrite: QueryRewritePort,
        fusion: ReciprocalRankFusion,
        stance_classifier: StanceClassifier,
        scorer: ScoreEvidenceCandidates,
    ) -> None:
        self._search_port = search_port
        self._query_rewrite = query_rewrite
        self._fusion = fusion
        self._stance_classifier = stance_classifier
        self._scorer = scorer

    async def execute(self, request: SearchEvidenceCandidatesRequest) -> SearchCandidatesResult:
        """Return scored candidates with stance and provenance for one claim."""
        rewrite = self._query_rewrite.rewrite(request.claim)
        rule = await self._search_port.authority_rule(request.claim_type)
        authority = AuthorityWeight.from_rule(rule, AuthorityTier.OTHER)
        passages = await self._search_port.search(
            rewrite.expanded, SnapshotId(request.snapshot_id), request.limit
        )
        candidates = [
            CandidateResult(
                passage_id=PassageId(passage.passage_id),
                stance=await self._stance_classifier.classify(ClaimText(request.claim), passage),
                score=self._scorer.score(
                    authority=authority,
                    lexical=1.0,
                    semantic=1.0,
                    recency=1.0,
                    directness=1.0,
                ),
                provenance=passage.provenance,
            )
            for passage in passages
        ]
        return SearchCandidatesResult(candidates=candidates)


class AssembleEvidencePack:
    """Build and freeze one balanced pack inside a single transaction."""

    def __init__(
        self,
        *,
        search_candidates: SearchEvidenceCandidates,
        packs: EvidencePackRepository,
        clock: Clock,
    ) -> None:
        self._search_candidates = search_candidates
        self._packs = packs
        self._clock = clock

    async def execute(self, request: AssembleEvidencePackRequest) -> EvidencePackResult:
        """Search both directions, record truthful absence, and freeze the pack."""
        raise NotImplementedError("AssembleEvidencePack.execute is a frozen stub")


class GetEvidencePack:
    """Read one stored pack and its trace."""

    def __init__(self, packs: EvidencePackRepository) -> None:
        self._packs = packs

    async def execute(self, request: GetEvidencePackRequest) -> EvidencePackResult:
        """Return the pack or raise :class:`EvidencePackNotFound`."""
        raise NotImplementedError("GetEvidencePack.execute is a frozen stub")


class GetScoreBreakdown:
    """Read the inspectable per-candidate weights of a stored pack."""

    def __init__(self, packs: EvidencePackRepository) -> None:
        self._packs = packs

    async def execute(self, request: GetScoreBreakdownRequest) -> ScoreBreakdownResult:
        """Return every candidate's component weights."""
        raise NotImplementedError("GetScoreBreakdown.execute is a frozen stub")


class ReweightEvidencePack:
    """Apply a new recency policy and persist the resulting pack version."""

    def __init__(
        self,
        *,
        packs: EvidencePackRepository,
        recency: ApplyRecencyPolicy,
        clock: Clock,
    ) -> None:
        self._packs = packs
        self._recency = recency
        self._clock = clock

    async def execute(self, request: ApplyRecencyPolicyRequest) -> EvidencePackResult:
        """Return a new frozen pack version; the previous version stays immutable."""
        raise NotImplementedError("ReweightEvidencePack.execute is a frozen stub")
