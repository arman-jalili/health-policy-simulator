"""Production adapters for retrieval ports (ADR-003, ADR-009).

Canonical: .pi/architecture/modules/evidence-retrieval.md

`CorpusPassageSearch` consumes only EvidenceCorpus' published ports: the index writer for ids, the
passage repository for `PassageView`, snapshots for the pinned document set and the authority-rule
repository for the rubric. It never reads `evidence_corpus_*` tables.
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from datetime import UTC, datetime

from evidence_corpus.application.ports import IndexWriterPort
from evidence_corpus.domain.published import PassageView, SnapshotIndexView
from evidence_corpus.domain.repositories import (
    AuthorityRuleRepository,
    CorpusSnapshotRepository,
    PassageRepository,
)
from evidence_corpus.domain.values import AuthorityRule, ClaimType
from evidence_retrieval.application.dto import RetrievalReadiness
from evidence_retrieval.application.ports import EmbeddingPort
from evidence_retrieval.domain.values import SnapshotId, StanceLabel
from shared.text_embedding import MODEL_ID, embed_texts


class CorpusPassageSearch:
    """Adapter from retrieval's port to EvidenceCorpus' published language."""

    def __init__(
        self,
        *,
        index: IndexWriterPort,
        passages: PassageRepository,
        snapshots: CorpusSnapshotRepository,
        authority_rules: AuthorityRuleRepository,
        embeddings: EmbeddingPort | None = None,
    ) -> None:
        self._index = index
        self._passages = passages
        self._snapshots = snapshots
        self._authority_rules = authority_rules
        self._embeddings = embeddings

    async def search(self, query: str, snapshot_id: SnapshotId, limit: int) -> list[PassageView]:
        allowed = set(await self._snapshots.list_document_ids(str(snapshot_id)))
        passage_ids = await self._index.search(query, limit)
        resolved = [await self._passages.get(passage_id) for passage_id in passage_ids]
        passages = [passage for passage in resolved if passage is not None]
        return [passage for passage in passages if not allowed or passage.document_id in allowed][
            :limit
        ]

    async def authority_rule(self, claim_type: ClaimType) -> AuthorityRule:
        return await self._authority_rules.for_claim_type(claim_type)

    async def snapshot_index(self, snapshot_id: SnapshotId) -> SnapshotIndexView:
        snapshot = await self._snapshots.get(str(snapshot_id))
        if snapshot is None:
            raise ValueError(f"snapshot {snapshot_id!r} does not exist")
        manifest = snapshot.index_manifest
        return SnapshotIndexView(
            index_version=manifest.index_version,
            embedding_model=manifest.embedding_model,
        )

    async def dense_search(
        self, query: str, snapshot_id: SnapshotId, limit: int
    ) -> list[tuple[PassageView, float]]:
        """Rank snapshot passages by vector similarity; the dense branch of hybrid retrieval.

        The prototype has no pgvector index column yet, so it embeds the pinned snapshot's
        passages at query time. That is still a real dense ranking and records the model that
        produced it; HNSW is the documented target state.
        """
        if self._embeddings is None:
            return []
        passages = await self._snapshot_passages(snapshot_id)
        if not passages:
            return []
        vectors = await self._embeddings.embed([query, *[p.text for p in passages]])
        if not vectors or not vectors[0]:
            return []
        query_vector = vectors[0]
        scored: list[tuple[PassageView, float]] = []
        for passage, vector in zip(passages, vectors[1:], strict=True):
            if not vector:
                continue
            similarity = sum(a * b for a, b in zip(query_vector, vector, strict=True))
            if similarity > 0.0:
                scored.append((passage, max(0.0, min(1.0, similarity))))
        scored.sort(key=lambda pair: (-pair[1], pair[0].passage_id))
        return scored[:limit]

    async def _snapshot_passages(self, snapshot_id: SnapshotId) -> list[PassageView]:
        allowed = await self._snapshots.list_document_ids(str(snapshot_id))
        passages: list[PassageView] = []
        for document_id in allowed:
            passages.extend(await self._passages.list_by_document(document_id))
        if passages:
            return passages
        # The in-memory E2E path seeds only the index; use it as a read-through fallback.
        list_cached = getattr(self._index, "list_by_document", None)
        if list_cached is None:
            return []
        cached: list[PassageView] = []
        for document_id in allowed:
            cached.extend(list_cached(document_id))
        return cached


class RuleBasedStanceModel:
    """Cheap deterministic stance baseline; an LLM strategy can replace it later."""

    _CONTRADICTION_CUES = ("nicht", "kein", "ohne", "wider", "senkt", "kürzt")
    _CONTEXT_CUES = ("kontext", "hintergrund", "vergleich")

    async def classify(self, claim: str, passage: PassageView) -> StanceLabel:
        text = passage.text.casefold()
        if any(cue in text for cue in self._CONTRADICTION_CUES):
            return StanceLabel.CONTRADICTING
        if any(cue in text for cue in self._CONTEXT_CUES):
            return StanceLabel.CONTEXTUAL
        return StanceLabel.SUPPORTING


class HashingEmbedding:
    """Vendor-free dense adapter used by the prototype; see ``shared.text_embedding``."""

    model_id = MODEL_ID

    async def embed(self, texts: Sequence[str]) -> list[list[float]]:
        return embed_texts(texts)


class LexicalEmbedding:
    """Explicit lexical-only adapter: no vector provider configured in this phase."""

    model_id = "none"

    async def embed(self, texts: Sequence[str]) -> list[list[float]]:
        return [[] for _ in texts]


class NoopReranker:
    """Cheap-mode reranker preserving the fusion order."""

    model_id = "none"

    async def rerank(
        self, claim: str, passages: Sequence[PassageView], limit: int
    ) -> list[PassageView]:
        return list(passages)[:limit]


class OverlapReranker:
    """Deterministic claim-overlap reranker; a cross-encoder can replace it behind the port."""

    model_id = "overlap-reranker-v1"
    _TERMS = re.compile(r"[a-z0-9äöüß]+")

    async def rerank(
        self, claim: str, passages: Sequence[PassageView], limit: int
    ) -> list[PassageView]:
        claim_terms = set(self._TERMS.findall(claim.casefold()))
        if not claim_terms:
            return list(passages)[:limit]

        def score(passage: PassageView) -> float:
            terms = set(self._TERMS.findall(passage.text.casefold()))
            return len(claim_terms & terms) / len(claim_terms)

        ordered = sorted(enumerate(passages), key=lambda pair: (-score(pair[1]), pair[0]))
        return [passage for _, passage in ordered[:limit]]


class StaticRetrievalReadiness:
    """Report the active retrieval capability and dependency reachability.

    ``detail`` is the truthful capability statement, not a deployment note: an unbound dense or
    reranker port is reported while the lexical path stays ready.
    """

    def __init__(
        self,
        embeddings_reachable: bool,
        reranker_reachable: bool,
        *,
        detail: str | None = None,
        mode: str = "lexical",
    ) -> None:
        self._embeddings = embeddings_reachable
        self._reranker = reranker_reachable
        self._detail = detail
        self._mode = mode

    async def check(self) -> RetrievalReadiness:
        detail = self._detail
        if not self._embeddings:
            detail = "embedding provider unreachable"
        elif not self._reranker:
            detail = "reranker unreachable"
        return RetrievalReadiness(
            embeddings_reachable=self._embeddings,
            reranker_reachable=self._reranker,
            detail=detail,
            mode=self._mode,
        )


class SystemClock:
    def now(self) -> datetime:
        return datetime.now(tz=UTC)
