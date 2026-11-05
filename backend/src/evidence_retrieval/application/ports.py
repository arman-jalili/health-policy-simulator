"""Ports consumed by the EvidenceRetrieval application layer.

Canonical: .pi/architecture/modules/evidence-retrieval.md

Ports isolate vendor choices (pgvector, embedding API, cross-encoder reranker) from use-case
orchestration. They are declared here, implemented in ``infrastructure/``, and never imported by
``domain/``.
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime
from typing import Protocol, runtime_checkable

from evidence_corpus.domain.published import PassageView
from evidence_retrieval.application.dto import RetrievalReadiness
from evidence_retrieval.domain.values import QueryRewrite


@runtime_checkable
class EmbeddingPort(Protocol):
    """Dense embedding client; metered like an LLM call (ADR-006)."""

    model_id: str

    async def embed(self, texts: Sequence[str]) -> list[list[float]]: ...


@runtime_checkable
class RerankerPort(Protocol):
    """Cross-encoder reranker; ``NoReranker`` is a valid cheap-mode adapter."""

    model_id: str

    async def rerank(
        self, claim: str, passages: Sequence[PassageView], limit: int
    ) -> list[PassageView]: ...


@runtime_checkable
class QueryRewritePort(Protocol):
    """Deterministic German expansion: compounds, umlauts, institutional synonyms."""

    def rewrite(self, query: str) -> QueryRewrite: ...


@runtime_checkable
class RetrievalReadinessPort(Protocol):
    """Probe embedding and reranker reachability for ``/readyz``."""

    async def check(self) -> RetrievalReadiness: ...


@runtime_checkable
class Clock(Protocol):
    """Injectable time source so pack timestamps and recency are reproducible in tests."""

    def now(self) -> datetime: ...
