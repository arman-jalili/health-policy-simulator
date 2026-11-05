"""Frozen application services of EvidenceRetrieval.

Canonical: .pi/architecture/modules/evidence-retrieval.md

Constructors, service names and ``execute`` signatures are frozen; the behaviour is implemented
against the domain contract and wired by the composition root.
"""

from __future__ import annotations

import re
from datetime import UTC, date, datetime

from evidence_corpus.domain.published import PassageView, SnapshotIndexView
from evidence_corpus.domain.values import AuthorityRule, AuthorityTier, SourceType
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
from evidence_retrieval.application.ports import Clock, QueryRewritePort, RerankerPort
from evidence_retrieval.domain.entities import EvidenceCandidate, RetrievalTrace
from evidence_retrieval.domain.errors import EvidencePackNotFound
from evidence_retrieval.domain.evidence_pack import EvidencePack
from evidence_retrieval.domain.repositories import EvidencePackRepository, PassageSearchPort
from evidence_retrieval.domain.services import (
    ApplyRecencyPolicy,
    ReciprocalRankFusion,
    ScoreEvidenceCandidates,
    StanceClassifier,
    directness_score,
)
from evidence_retrieval.domain.values import (
    AuthorityWeight,
    ClaimText,
    EvidenceScore,
    PackId,
    PassageId,
    QueryRewrite,
    RecencyPolicy,
    SnapshotId,
    StanceAssessment,
    StanceLabel,
)
from shared.ids import new_id
from shared.metrics import METRICS

_TERM_PATTERN = re.compile(r"[a-z0-9äöüß]+")
_GERMAN_STOPWORDS = frozenset({"der", "die", "das", "und", "werden", "or"})


def _lexical_relevance(query: str, text: str) -> float:
    """Return the fraction of distinct query terms present in the passage.

    This is a real measurement of the lexical hit, not a constant. It intentionally uses term
    presence rather than ORM rank so the value is reproducible across in-memory and PostgreSQL.
    """
    terms = {
        term for term in _TERM_PATTERN.findall(query.casefold()) if term not in _GERMAN_STOPWORDS
    }
    if not terms:
        return 0.0
    text_terms = set(_TERM_PATTERN.findall(text.casefold()))
    return len(terms & text_terms) / len(terms)


def _tier_for(source_type: SourceType) -> AuthorityTier:
    """Map a declared corpus source type to its rubric tier; unknown is never scorable."""
    try:
        return AuthorityTier(source_type.value)
    except ValueError as exc:
        raise ValueError(f"source type {source_type.value!r} cannot be scored") from exc


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
        recency: ApplyRecencyPolicy | None = None,
        clock: Clock | None = None,
        reranker: RerankerPort | None = None,
    ) -> None:
        self._search_port = search_port
        self._query_rewrite = query_rewrite
        self._fusion = fusion
        self._stance_classifier = stance_classifier
        self._scorer = scorer
        self._recency = recency or ApplyRecencyPolicy()
        self._clock = clock
        self._reranker = reranker

    async def execute(self, request: SearchEvidenceCandidatesRequest) -> SearchCandidatesResult:
        """Return scored candidates with stance, derived components and provenance for one claim."""
        rewrite = self._query_rewrite.rewrite(request.claim)
        rule = await self._search_port.authority_rule(request.claim_type)
        snapshot_id = SnapshotId(request.snapshot_id)
        index = await self._snapshot_index(snapshot_id)
        lexical = await self._search_port.search(rewrite.expanded, snapshot_id, request.limit)
        dense: list[tuple[PassageView, float]] = []
        dense_lookup = getattr(self._search_port, "dense_search", None)
        if index.embedding_model != "none" and dense_lookup is not None:
            dense = list(await dense_lookup(rewrite.expanded, snapshot_id, request.limit))
        mode = "lexical+dense" if dense else "lexical"
        fused = self._fusion.fuse([lexical, [hit[0] for hit in dense]]) if dense else lexical
        if self._reranker is not None:
            passages = await self._reranker.rerank(request.claim, fused, request.limit)
        else:
            passages = fused
        semantic_scores = {hit[0].passage_id: hit[1] for hit in dense}
        as_of = self._clock.now().date() if self._clock is not None else datetime.now(tz=UTC).date()
        policy = RecencyPolicy()
        candidates = [
            await self._candidate(
                request=request,
                rewrite_expanded=rewrite.expanded,
                rule=rule,
                passage=passage,
                policy=policy,
                as_of=as_of,
                semantic=semantic_scores.get(passage.passage_id, 0.0),
            )
            for passage in passages
        ]
        METRICS.increment(
            "evidence_retrieval_searches_total",
            {"claim_type": request.claim_type.value, "mode": mode},
        )
        METRICS.increment(
            "evidence_retrieval_candidates_total",
            {"claim_type": request.claim_type.value},
            len(candidates),
        )
        return SearchCandidatesResult(
            candidates=candidates,
            retrieval_mode=mode,
            embedding_model=index.embedding_model,
            reranker_model=self._reranker.model_id if self._reranker is not None else "none",
            index_version=index.index_version,
            query_rewrite=rewrite.expanded,
        )

    async def _candidate(
        self,
        *,
        request: SearchEvidenceCandidatesRequest,
        rewrite_expanded: str,
        rule: AuthorityRule,
        passage: PassageView,
        policy: RecencyPolicy,
        as_of: date,
        semantic: float,
    ) -> CandidateResult:
        assessment = await self._assess(ClaimText(request.claim), passage)
        authority = AuthorityWeight.from_rule(rule, _tier_for(passage.source_type))
        recency = self._recency.apply(
            policy=policy,
            published_on=passage.provenance.published_on,
            source_type=passage.source_type,
            as_of=as_of,
        )
        return CandidateResult(
            passage_id=PassageId(passage.passage_id),
            stance=assessment.label,
            score=self._scorer.score(
                authority=authority,
                lexical=_lexical_relevance(rewrite_expanded, passage.text),
                semantic=semantic,
                recency=recency,
                directness=assessment.directness,
            ),
            provenance=passage.provenance,
            source_type=passage.source_type,
        )

    async def _assess(self, claim: ClaimText, passage: PassageView) -> StanceAssessment:
        assess = getattr(self._stance_classifier, "assess", None)
        if assess is not None:
            result = await assess(claim, passage)
            if isinstance(result, StanceAssessment):
                return result
        label = await self._stance_classifier.classify(claim, passage)
        return StanceAssessment(label=label, directness=directness_score(str(claim), passage.text))

    async def _snapshot_index(self, snapshot_id: SnapshotId) -> SnapshotIndexView:
        return await self._search_port.snapshot_index(snapshot_id)


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
        rewrite = QueryRewrite(
            original=request.claim,
            expanded=result.query_rewrite or request.claim,
        )
        trace = RetrievalTrace(
            embedding_model=result.embedding_model,
            reranker_model=result.reranker_model,
            query_rewrite=rewrite,
            stance_counts={
                stance: sum(1 for c in result.candidates if c.stance is stance)
                for stance in StanceLabel
            },
            retrieval_mode=result.retrieval_mode,
            index_version=result.index_version,
        )
        pack = EvidencePack(
            id=PackId(new_id("evp")),
            claim=ClaimText(request.claim),
            snapshot_id=SnapshotId(request.snapshot_id),
            index_version=result.index_version,
            trace=trace,
        )
        for candidate in result.candidates:
            pack.add_candidate(
                EvidenceCandidate(
                    passage_id=candidate.passage_id,
                    stance=candidate.stance,
                    score=candidate.score,
                    provenance=candidate.provenance,
                    source_type=candidate.source_type,
                )
            )
        if not any(c.stance is StanceLabel.CONTRADICTING for c in result.candidates):
            pack.record_absence([request.claim], "no contradicting passage above threshold")
        pack.freeze()
        pack.frozen_at = self._clock.now()
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
            retrieval_mode=pack.trace.retrieval_mode,
            index_version=pack.trace.index_version,
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
                retrieval_mode=stored.trace.retrieval_mode,
                index_version=stored.trace.index_version,
            ),
        )
        as_of = self._clock.now().date()
        for candidate in stored.candidates:
            provenance = candidate.provenance
            recency = (
                self._recency.apply(
                    policy=request.policy,
                    published_on=provenance.published_on,
                    source_type=candidate.source_type,
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
                    source_type=candidate.source_type,
                )
            )
        if stored.absence is not None:
            rewritten.record_absence(list(stored.absence.queries), stored.absence.reason)
        rewritten.freeze()
        await self._packs.save(rewritten)
        METRICS.increment("evidence_retrieval_reweights_total")
        return _pack_result(rewritten)
