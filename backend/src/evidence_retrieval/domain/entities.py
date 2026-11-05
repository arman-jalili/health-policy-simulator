"""Frozen entities of the EvidenceRetrieval context.

Canonical: .pi/architecture/modules/evidence-retrieval.md

CONTRACT FREEZE — field sets and identity rules are frozen. Behaviour belongs to the aggregate and
scoring implementation issues.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from evidence_corpus.domain.published import ProvenanceView
from evidence_corpus.domain.values import SourceType
from evidence_retrieval.domain.values import (
    EvidenceScore,
    PassageId,
    QueryRewrite,
    StanceLabel,
)


@dataclass(slots=True)
class EvidenceCandidate:
    """One retrieved passage annotated with stance, score and corpus provenance.

    Identity is ``passage_id``; a candidate is rescored in place before the pack freezes. A missing
    provenance is representable so :meth:`EvidencePack.freeze` can reject it with a precise error.
    """

    passage_id: PassageId
    stance: StanceLabel
    score: EvidenceScore
    provenance: ProvenanceView | None
    source_type: SourceType = SourceType.OTHER


@dataclass(frozen=True, slots=True)
class RetrievalTrace:
    """Reproducibility record: index models, query rewrite and stance counts (invariant 5).

    Identity is the owning pack id plus attempt; the trace itself is an immutable record.
    """

    embedding_model: str
    reranker_model: str
    query_rewrite: QueryRewrite
    stance_counts: Mapping[StanceLabel, int]
    retrieval_mode: str = "lexical"
    index_version: str = "unknown"

    def __post_init__(self) -> None:
        if not self.embedding_model.strip():
            raise ValueError("RetrievalTrace.embedding_model must be non-empty")
        if not self.reranker_model.strip():
            raise ValueError("RetrievalTrace.reranker_model must be non-empty")
        if self.retrieval_mode not in {"lexical", "dense", "lexical+dense"}:
            raise ValueError("RetrievalTrace.retrieval_mode is not a declared mode")
        if not self.index_version.strip():
            raise ValueError("RetrievalTrace.index_version must be non-empty")
