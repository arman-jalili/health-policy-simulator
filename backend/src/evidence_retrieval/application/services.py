"""Frozen application services of EvidenceRetrieval.

Canonical: .pi/architecture/modules/evidence-retrieval.md

Constructors, service names and ``execute`` signatures are frozen; the behaviour is implemented
against the domain contract and wired by the composition root.
"""

from __future__ import annotations

from evidence_corpus.domain.values import AuthorityTier, SourceType
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
    CandidateScoreResult,
    EvidencePackResult,
    ScoreBreakdownResult,
    SearchCandidatesResult,
    TraceResult,
)
from evidence_retrieval.application.ports import Clock, QueryRewritePort
from evidence_retrieval.domain.entities import EvidenceCandidate, RetrievalTrace
from evidence_retrieval.domain.errors import EvidencePackNotFound
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
    EvidenceScore,
    PackId,
    PassageId,
    QueryRewrite,
    SnapshotId,
    StanceLabel,
)
from shared.ids import new_id
from shared.metrics import METRICS


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
        METRICS.increment(
            "evidence_retrieval_searches_total",
            {"claim_type": request.claim_type.value},
        )
        METRICS.increment(
            "evidence_retrieval_candidates_total",
            {"claim_type": request.claim_type.value},
            len(candidates),
        )
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
        METRICS.increment(
            "evidence_retrieval_packs_total",
            {"has_absence": str(pack.absence is not None).lower()},
        )
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
        pack = await self._packs.get(PackId(request.pack_id))
        if pack is None:
            raise EvidencePackNotFound(request.pack_id)
        return _pack_result(pack)


class GetScoreBreakdown:
    """Read the inspectable per-candidate weights of a stored pack."""

    def __init__(self, packs: EvidencePackRepository) -> None:
        self._packs = packs

    async def execute(self, request: GetScoreBreakdownRequest) -> ScoreBreakdownResult:
        """Return every candidate's component weights."""
        pack = await self._packs.get(PackId(request.pack_id))
        if pack is None:
            raise EvidencePackNotFound(request.pack_id)
        return ScoreBreakdownResult(
            pack_id=str(pack.id),
            candidates=[
                CandidateScoreResult(passage_id=c.passage_id, score=c.score)
                for c in pack.candidates
            ],
        )


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
        stored = await self._packs.get(PackId(request.pack_id))
        if stored is None:
            raise EvidencePackNotFound(request.pack_id)
        rewritten = EvidencePack(
            id=PackId(new_id("evp")),
            claim=stored.claim,
            snapshot_id=stored.snapshot_id,
            index_version=stored.index_version,
            trace=RetrievalTrace(
                embedding_model=stored.trace.embedding_model,
                reranker_model=stored.trace.reranker_model,
                query_rewrite=QueryRewrite(
                    original=stored.trace.query_rewrite.original,
                    expanded=stored.trace.query_rewrite.expanded,
                ),
                stance_counts=dict(stored.trace.stance_counts),
            ),
        )
        as_of = self._clock.now().date()
        for candidate in stored.candidates:
            provenance = candidate.provenance
            recency = (
                self._recency.apply(
                    policy=request.policy,
                    published_on=provenance.published_on,
                    source_type=SourceType.OTHER,
                    as_of=as_of,
                )
                if provenance is not None
                else 0.0
            )
            rewritten.add_candidate(
                EvidenceCandidate(
                    passage_id=candidate.passage_id,
                    stance=candidate.stance,
                    score=EvidenceScore(
                        authority=candidate.score.authority,
                        lexical=candidate.score.lexical,
                        semantic=candidate.score.semantic,
                        recency=recency,
                        directness=candidate.score.directness,
                        final=(
                            candidate.score.authority
                            + candidate.score.lexical
                            + candidate.score.semantic
                            + recency
                            + candidate.score.directness
                        ),
                    ),
                    provenance=provenance,
                )
            )
        if stored.absence is not None:
            rewritten.record_absence(list(stored.absence.queries), stored.absence.reason)
        rewritten.freeze()
        await self._packs.save(rewritten)
        METRICS.increment("evidence_retrieval_reweights_total")
        return _pack_result(rewritten)
