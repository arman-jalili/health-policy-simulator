"""Composition contract for EvidenceRetrieval (ADR-001).

Canonical: .pi/architecture/modules/evidence-retrieval.md

The container is frozen now; the wiring issue binds real pgvector/tsvector adapters, the embedding
and reranker clients, and mounts the router in ``shared.app``.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass

from evidence_corpus.composition import CorpusContainer
from evidence_retrieval.application.ports import (
    Clock,
    EmbeddingPort,
    QueryRewritePort,
    RerankerPort,
    RetrievalReadinessPort,
)
from evidence_retrieval.application.services import (
    AssembleEvidencePack,
    GetEvidencePack,
    GetScoreBreakdown,
    ReweightEvidencePack,
    SearchEvidenceCandidates,
)
from evidence_retrieval.domain.repositories import EvidencePackRepository, PassageSearchPort
from evidence_retrieval.domain.services import (
    ApplyRecencyPolicy,
    ReciprocalRankFusion,
    ScoreEvidenceCandidates,
    StanceClassifier,
)
from evidence_retrieval.infrastructure.adapters import (
    CorpusPassageSearch,
    HashingEmbedding,
    OverlapReranker,
    RuleBasedStanceModel,
    StaticRetrievalReadiness,
    SystemClock,
)
from evidence_retrieval.infrastructure.memory import InMemoryEvidencePackRepository
from evidence_retrieval.infrastructure.query_rewrite import GermanQueryRewrite
from evidence_retrieval.infrastructure.repository.sqlalchemy import (
    SqlAlchemyEvidencePackRepository,
)
from shared.config import Settings
from shared.db import Database, UnitOfWork
from shared.enums import Persistence


@dataclass
class EvidenceRetrievalContainer:
    """Wired use cases, domain services and ports for one application process."""

    packs: EvidencePackRepository
    passage_search: PassageSearchPort
    embeddings: EmbeddingPort
    reranker: RerankerPort
    query_rewrite: QueryRewritePort
    readiness: RetrievalReadinessPort
    fusion: ReciprocalRankFusion
    stance_classifier: StanceClassifier
    scorer: ScoreEvidenceCandidates
    recency: ApplyRecencyPolicy
    clock: Clock
    search_candidates: SearchEvidenceCandidates
    assemble_pack: AssembleEvidencePack
    get_pack: GetEvidencePack
    get_score_breakdown: GetScoreBreakdown
    reweight_pack: ReweightEvidencePack
    unit_of_work: UnitOfWork | None = None

    @asynccontextmanager
    async def transaction(self) -> AsyncIterator[None]:
        """Run one logical use case in a single transaction (no-op for in-memory)."""
        if self.unit_of_work is None:
            yield
            return
        async with self.unit_of_work.transaction():
            yield


def build_container(
    settings: Settings,
    database: Database | None = None,
    actor: str = "system",
    corpus: CorpusContainer | None = None,
) -> EvidenceRetrievalContainer:
    """Select and construct adapters for the configured persistence family.

    Retrieval consumes corpus ports only (ADR-003): the index writer, passage repository, snapshot
    repository and authority-rule repository. It never imports corpus persistence adapters or reads
    corpus tables.
    """
    if corpus is None:
        raise ValueError("evidence-retrieval requires the wired EvidenceCorpus container")
    if settings.persistence is Persistence.MEMORY:
        packs: EvidencePackRepository = InMemoryEvidencePackRepository()
        unit_of_work = None
    else:
        if database is None:
            raise ValueError(
                "PERSISTENCE=postgres requires a Database; the application shell owns the engine"
            )
        packs = SqlAlchemyEvidencePackRepository(database.session_factory)
        unit_of_work = UnitOfWork(database.session_factory)

    embeddings = HashingEmbedding()
    reranker = OverlapReranker()
    passage_search = CorpusPassageSearch(
        index=corpus.index_writer,
        passages=corpus.passages,
        snapshots=corpus.snapshots,
        authority_rules=corpus.authority_rules,
        embeddings=embeddings,
    )
    query_rewrite = GermanQueryRewrite()
    fusion = ReciprocalRankFusion()
    stance_classifier = StanceClassifier(RuleBasedStanceModel())
    scorer = ScoreEvidenceCandidates()
    clock = SystemClock()
    recency = ApplyRecencyPolicy()
    search_candidates = SearchEvidenceCandidates(
        search_port=passage_search,
        query_rewrite=query_rewrite,
        fusion=fusion,
        stance_classifier=stance_classifier,
        scorer=scorer,
        recency=recency,
        clock=clock,
        reranker=reranker,
    )
    return EvidenceRetrievalContainer(
        packs=packs,
        passage_search=passage_search,
        embeddings=embeddings,
        reranker=reranker,
        query_rewrite=query_rewrite,
        readiness=StaticRetrievalReadiness(
            True,
            True,
            detail="lexical+dense (hashing-char3gram-v1); reranker overlap-reranker-v1",
            mode="lexical+dense",
        ),
        fusion=fusion,
        stance_classifier=stance_classifier,
        scorer=scorer,
        recency=recency,
        clock=clock,
        search_candidates=search_candidates,
        assemble_pack=AssembleEvidencePack(
            search_candidates=search_candidates, packs=packs, clock=clock
        ),
        get_pack=GetEvidencePack(packs),
        get_score_breakdown=GetScoreBreakdown(packs),
        reweight_pack=ReweightEvidencePack(packs=packs, recency=recency, clock=clock),
        unit_of_work=unit_of_work,
    )
