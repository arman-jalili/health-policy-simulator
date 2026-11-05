"""Composition contract for EvidenceRetrieval (ADR-001).

Canonical: .pi/architecture/modules/evidence-retrieval.md

The container is frozen now; the wiring issue binds real pgvector/tsvector adapters, the embedding
and reranker clients, and mounts the router in ``shared.app``.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass

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
from shared.config import Settings
from shared.db import Database, UnitOfWork


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
) -> EvidenceRetrievalContainer:
    """Select and construct adapters for the configured persistence family."""
    raise NotImplementedError(
        f"TODO(wiring): build evidence-retrieval for persistence={settings.persistence} "
        f"and {'a database' if database is not None else 'no database'} (actor={actor})"
    )
