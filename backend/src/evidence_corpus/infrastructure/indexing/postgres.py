"""PostgreSQL index writer: `tsvector` rows plus the published index manifest.

Canonical: .pi/architecture/decisions/ADR-002-data-storage-strategy.md

Indexing is idempotent per document: existing rows for the document are removed before the new
passages are inserted, so re-running an ingestion never duplicates results. The manifest version is
a hash of the indexed passage ids, which makes it reproducible.
"""

from __future__ import annotations

import hashlib
from collections.abc import Sequence
from datetime import UTC, datetime

from sqlalchemy import delete, select, text, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from evidence_corpus.application.dto import IndexManifestView
from evidence_corpus.domain.published import PassageView
from evidence_corpus.infrastructure.indexing.models import IndexedPassage, IndexManifestRow
from shared.text_embedding import MODEL_ID


def _version(indexed_ids: list[str]) -> str:
    digest = hashlib.sha256("|".join(indexed_ids).encode("utf-8")).hexdigest()[:12]
    return f"idx-{digest}"


class PostgresIndexWriter:
    """Implements :class:`evidence_corpus.application.ports.IndexWriterPort`."""

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    async def upsert_passages(
        self, document_id: str, passages: Sequence[PassageView]
    ) -> IndexManifestView:
        async with self._session_factory() as session, session.begin():
            await session.execute(
                delete(IndexedPassage).where(IndexedPassage.document_id == document_id)
            )
            for passage in passages:
                session.add(
                    IndexedPassage(
                        passage_id=passage.passage_id,
                        document_id=document_id,
                        article_id=passage.article_id,
                        text=passage.text,
                        speaker_kind=str(passage.speaker_kind),
                        citable=passage.citable,
                        page_from=passage.provenance.page_from,
                        page_to=passage.provenance.page_to,
                        offset_start=passage.provenance.offsets.start,
                        offset_end=passage.provenance.offsets.end,
                    )
                )
            await session.flush()

            total = await session.scalar(select(text("count(*)")).select_from(IndexedPassage))
            indexed_ids = list(
                await session.scalars(
                    select(IndexedPassage.passage_id).order_by(IndexedPassage.passage_id)
                )
            )
            manifest = IndexManifestView(
                index_version=_version(indexed_ids),
                embedding_model=MODEL_ID,
                searchable_since=datetime.now(tz=UTC),
                passage_count=int(total or 0),
            )

            await session.execute(update(IndexManifestRow).values(is_current=False))
            statement = pg_insert(IndexManifestRow).values(
                index_version=manifest.index_version,
                embedding_model=manifest.embedding_model,
                searchable_since=manifest.searchable_since,
                passage_count=manifest.passage_count,
                is_current=True,
            )
            await session.execute(
                statement.on_conflict_do_update(
                    index_elements=[IndexManifestRow.index_version],
                    set_={
                        "embedding_model": statement.excluded.embedding_model,
                        "passage_count": statement.excluded.passage_count,
                        "searchable_since": statement.excluded.searchable_since,
                        "is_current": True,
                    },
                )
            )
        return manifest

    async def revert_passage(self, passage_id: str, reason: str) -> None:
        async with self._session_factory() as session, session.begin():
            await session.execute(
                delete(IndexedPassage).where(IndexedPassage.passage_id == passage_id)
            )

    async def search(self, query: str, limit: int = 20) -> list[str]:
        """Lexical search using the generated `tsvector`; returns passage ids in rank order."""
        statement = (
            select(IndexedPassage.passage_id)
            .where(
                IndexedPassage.tsv.op("@@")(
                    text("plainto_tsquery('german', :query)").bindparams(query=query)
                )
            )
            .order_by(
                text("ts_rank(tsv, plainto_tsquery('german', :query)) desc").bindparams(query=query)
            )
            .limit(limit)
        )
        async with self._session_factory() as session:
            return list(await session.scalars(statement))
