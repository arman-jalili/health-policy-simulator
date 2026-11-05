"""Production adapters for retrieval ports (ADR-003, ADR-009).

Canonical: .pi/architecture/modules/evidence-retrieval.md

`CorpusPassageSearch` consumes only EvidenceCorpus' published ports: the index writer for ids, the
passage repository for `PassageView`, snapshots for the pinned document set and the authority-rule
repository for the rubric. It never reads `evidence_corpus_*` tables.
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC, datetime
from typing import Any, Protocol, cast

from evidence_corpus.domain.published import PassageView
from evidence_corpus.domain.repositories import (
    AuthorityRuleRepository,
    CorpusSnapshotRepository,
    PassageRepository,
)
from evidence_corpus.domain.values import AuthorityRule, ClaimType
from evidence_retrieval.application.dto import RetrievalReadiness
from evidence_retrieval.domain.values import SnapshotId, StanceLabel


class _SearchableIndex(Protocol):
    def search(self, query: str, limit: int = 20) -> Any: ...


class CorpusPassageSearch:
    """Adapter from retrieval's port to EvidenceCorpus' published language."""

    def __init__(
        self,
        *,
        index: _SearchableIndex,
        passages: PassageRepository,
        snapshots: CorpusSnapshotRepository,
        authority_rules: AuthorityRuleRepository,
    ) -> None:
        self._index = index
        self._passages = passages
        self._snapshots = snapshots
        self._authority_rules = authority_rules

    async def search(self, query: str, snapshot_id: SnapshotId, limit: int) -> list[PassageView]:
        allowed = set(await self._snapshots.list_document_ids(str(snapshot_id)))
        raw = self._search_index(query, limit)
        if raw and isinstance(raw[0], str):
            resolved = [await self._passages.get(passage_id) for passage_id in raw]
            passages = [passage for passage in resolved if passage is not None]
        else:
            passages = cast(list[PassageView], raw)
        return [passage for passage in passages if not allowed or passage.document_id in allowed][
            :limit
        ]

    async def authority_rule(self, claim_type: ClaimType) -> AuthorityRule:
        return await self._authority_rules.for_claim_type(claim_type)

    def _search_index(self, query: str, limit: int) -> Any:
        try:
            return self._index.search(query, limit)
        except TypeError:
            return self._index.search(query)


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


class LexicalEmbedding:
    """Explicit lexical-only adapter: no vector provider configured in this phase."""

    async def embed(self, texts: Sequence[str]) -> list[list[float]]:
        return [[] for _ in texts]


class NoopReranker:
    """Cheap-mode reranker preserving the fusion order."""

    async def rerank(
        self, claim: str, passages: Sequence[PassageView], limit: int
    ) -> list[PassageView]:
        return list(passages)[:limit]


class StaticRetrievalReadiness:
    """Report configured dependency reachability; false is a hard readiness failure."""

    def __init__(self, embeddings_reachable: bool, reranker_reachable: bool) -> None:
        self._embeddings = embeddings_reachable
        self._reranker = reranker_reachable

    async def check(self) -> RetrievalReadiness:
        detail = None
        if not self._embeddings:
            detail = "embedding provider unreachable"
        elif not self._reranker:
            detail = "reranker unreachable"
        return RetrievalReadiness(
            embeddings_reachable=self._embeddings,
            reranker_reachable=self._reranker,
            detail=detail,
        )


class SystemClock:
    def now(self) -> datetime:
        return datetime.now(tz=UTC)
