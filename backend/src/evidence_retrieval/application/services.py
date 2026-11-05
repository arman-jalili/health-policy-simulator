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
    AbsenceResult,
    CandidateResult,
    EvidencePackResult,
    ScoreBreakdownResult,
    SearchCandidatesResult,
    TraceResult,
)
from evidence_retrieval.application.ports import Clock, QueryRewritePort
from evidence_retrieval.domain.entities import EvidenceCandidate, RetrievalTrace
from evidence_retrieval.domain.evidence_pack import EvidencePack
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
    PackId,
    PassageId,
    QueryRewrite,
    SnapshotId,
    StanceLabel,
)
from shared.ids import new_id


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
        result = await self._search_candidates.execute(
            SearchEvidenceCandidatesRequest(
                claim=request.claim,
                claim_type=request.claim_type,
                snapshot_id=request.snapshot_id,
            )
        )
        rewrite = QueryRewrite(original=request.claim, expanded=request.claim)
        trace = RetrievalTrace(
            embedding_model="configured",
            reranker_model="configured",
            query_rewrite=rewrite,
            stance_counts={
                stance: sum(1 for c in result.candidates if c.stance is stance)
                for stance in StanceLabel
            },
        )
        pack = EvidencePack(
            id=PackId(new_id("evp")),
            claim=ClaimText(request.claim),
            snapshot_id=SnapshotId(request.snapshot_id),
            index_version="snapshot:" + request.snapshot_id,
            trace=trace,
        )
        for candidate in result.candidates:
            pack.add_candidate(
                EvidenceCandidate(
                    passage_id=candidate.passage_id,
                    stance=candidate.stance,
                    score=candidate.score,
                    provenance=candidate.provenance,
                )
            )
        if not any(c.stance is StanceLabel.CONTRADICTING for c in result.candidates):
            pack.record_absence([request.claim], "no contradicting passage above threshold")
        pack.freeze()
        await self._packs.save(pack)
        return _pack_result(pack)


def _pack_result(pack: EvidencePack) -> EvidencePackResult:
    """Map the aggregate to the application result consumed by the HTTP layer."""
    if pack.frozen_at is None:
        raise RuntimeError("a pack must be frozen before it is mapped to a result")
    return EvidencePackResult(
        pack_id=str(pack.id),
        claim=str(pack.claim),
        snapshot_id=str(pack.snapshot_id),
        index_version=pack.index_version,
        candidates=[
            CandidateResult(
                passage_id=candidate.passage_id,
                stance=candidate.stance,
                score=candidate.score,
                provenance=candidate.provenance,
            )
            for candidate in pack.candidates
        ],
        absence=(
            AbsenceResult(
                queries=list(pack.absence.queries),
                snapshot_id=str(pack.absence.snapshot_id),
                reason=pack.absence.reason,
            )
            if pack.absence is not None
            else None
        ),
        trace=TraceResult(
            embedding_model=pack.trace.embedding_model,
            reranker_model=pack.trace.reranker_model,
            query_rewrite=pack.trace.query_rewrite.expanded,
            stance_counts=dict(pack.trace.stance_counts),
        ),
        frozen_at=pack.frozen_at,
    )


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
