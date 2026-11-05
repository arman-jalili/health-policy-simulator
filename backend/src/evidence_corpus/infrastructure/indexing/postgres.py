"""PostgreSQL index writer: `tsvector` plus pgvector upserts.

Canonical: .pi/architecture/decisions/ADR-002-data-storage-strategy.md

CONTRACT FREEZE — adapter surface only; index behaviour lands with the `IndexIngestedPassages`
implementation issue.
"""

from __future__ import annotations

from collections.abc import Sequence

from evidence_corpus.application.dto import IndexManifestView
from evidence_corpus.domain.published import PassageView


class PostgresIndexWriter:
    """Implements :class:`evidence_corpus.application.ports.IndexWriterPort`."""

    async def upsert_passages(
        self, document_id: str, passages: Sequence[PassageView]
    ) -> IndexManifestView:
        raise NotImplementedError("PostgresIndexWriter.upsert_passages is a frozen stub")

    async def revert_passage(self, passage_id: str, reason: str) -> None:
        raise NotImplementedError("PostgresIndexWriter.revert_passage is a frozen stub")
