"""In-memory index writer used by tests and the composition root until PostgreSQL is wired."""

from __future__ import annotations

import hashlib
from collections.abc import Sequence
from datetime import UTC, datetime

from evidence_corpus.application.dto import IndexManifestView
from evidence_corpus.domain.published import PassageView


class InMemoryIndexWriter:
    """Implements :class:`evidence_corpus.application.ports.IndexWriterPort`."""

    def __init__(self) -> None:
        self._rows: dict[str, PassageView] = {}
        self._passages_by_document: dict[str, set[str]] = {}
        self.german_stopwords = ("der", "die", "das", "und", "werden")

    async def upsert_passages(
        self, document_id: str, passages: Sequence[PassageView]
    ) -> IndexManifestView:
        for previous in self._passages_by_document.get(document_id, set()):
            self._rows.pop(previous, None)

        self._passages_by_document[document_id] = set()
        for passage in passages:
            self._rows[passage.passage_id] = passage
            self._passages_by_document[document_id].add(passage.passage_id)

        ordered = sorted(self._rows)
        index_version = "idx-" + hashlib.sha256("|".join(ordered).encode()).hexdigest()[:12]
        return IndexManifestView(
            index_version=index_version,
            embedding_model="none",
            searchable_since=datetime.now(tz=UTC),
            passage_count=len(self._rows),
        )

    async def revert_passage(self, passage_id: str, reason: str) -> None:
        self._rows.pop(passage_id, None)

    def search(self, query: str) -> list[PassageView]:
        terms = [term for term in query.lower().split() if term]
        return [
            passage
            for passage in self._rows.values()
            if all(term in passage.text.lower() for term in terms)
        ]
