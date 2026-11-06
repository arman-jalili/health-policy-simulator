"""In-memory index writer selected by ``PERSISTENCE=memory`` (tests, database-less demo)."""

from __future__ import annotations

import hashlib
from collections.abc import Sequence
from datetime import UTC, datetime

from evidence_corpus.application.dto import IndexManifestView
from evidence_corpus.domain.published import PassageView
from evidence_corpus.infrastructure.indexing.lexical import (
    is_disjunctive,
    query_terms,
    term_prefix_matches,
    text_tokens,
)
from shared.text_embedding import MODEL_ID


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
            embedding_model=MODEL_ID,
            searchable_since=datetime.now(tz=UTC),
            passage_count=len(self._rows),
        )

    async def revert_passage(self, passage_id: str, reason: str) -> None:
        self._rows.pop(passage_id, None)

    def list_by_document(self, document_id: str) -> list[PassageView]:
        """Read-through for the in-memory retrieval E2E path."""
        return [
            self._rows[passage_id]
            for passage_id in sorted(self._passages_by_document.get(document_id, set()))
        ]

    async def search(self, query: str, limit: int = 20) -> list[str]:
        """Return passage ids in rank order, matching the PostgreSQL writer's port."""
        terms = tuple(term for term in query_terms(query) if term not in self.german_stopwords)
        if not terms:
            return []
        require_all = not is_disjunctive(query)
        matches: list[str] = []
        for passage_id, passage in self._rows.items():
            tokens = tuple(
                token for token in text_tokens(passage.text) if token not in self.german_stopwords
            )
            results = [term_prefix_matches(term, tokens) for term in terms]
            if all(results) if require_all else any(results):
                matches.append(passage_id)
        return matches[:limit]
