"""Integration: the PostgreSQL index writer must make passages searchable via `tsvector`.

Requires ``DATABASE_URL`` pointing at PostgreSQL with pgvector (see compose.yaml).
"""

from __future__ import annotations

import os
from collections.abc import AsyncIterator
from datetime import date

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from evidence_corpus.domain.published import PassageView, ProvenanceView
from evidence_corpus.domain.values import Offsets, SpeakerKind
from evidence_corpus.infrastructure.indexing.postgres import PostgresIndexWriter
from shared.config import get_settings

DATABASE_URL = os.environ.get("DATABASE_URL") or os.environ.get("HPS_TEST_DATABASE_URL")

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        not DATABASE_URL,
        reason="DATABASE_URL is not set (start compose.yaml and export it)",
    ),
]


@pytest.fixture
def alembic_config(monkeypatch: pytest.MonkeyPatch) -> Config:
    monkeypatch.setenv("DATABASE_URL", DATABASE_URL or "")
    get_settings.cache_clear()
    config = Config("alembic.ini")
    config.set_main_option("script_location", "migrations")
    return config


def _passage(passage_id: str, content: str) -> PassageView:
    return PassageView(
        passage_id=passage_id,
        article_id="art_1",
        document_id="doc_1",
        text=content,
        provenance=ProvenanceView(
            outlet="Der Standard",
            published_on=date(2026, 10, 1),
            medium="print",
            page_from=3,
            page_to=3,
            offsets=Offsets(0, len(content)),
            source_uri="s3://corpus/std.pdf",
        ),
        speaker_kind=SpeakerKind.INSTITUTION,
        citable=True,
    )


@pytest.fixture(scope="module")
def migrated() -> None:
    """Apply migrations outside the event loop: Alembic's env.py calls asyncio.run()."""
    os.environ.setdefault("DATABASE_URL", DATABASE_URL or "")
    get_settings.cache_clear()
    config = Config("alembic.ini")
    config.set_main_option("script_location", "migrations")
    command.upgrade(config, "head")


@pytest.fixture
async def writer(migrated: None) -> AsyncIterator[PostgresIndexWriter]:
    engine = create_async_engine(DATABASE_URL or "")
    try:
        yield PostgresIndexWriter(async_sessionmaker(engine, expire_on_commit=False))
    finally:
        await engine.dispose()


async def test_german_terms_are_searchable_and_reindexing_is_idempotent(
    writer: PostgresIndexWriter,
) -> None:
    passages = [
        _passage("psg_index_a", "Die Kassenstellen werden aufgestockt."),
        _passage("psg_index_b", "Die Spitalsreform ist beschlossen."),
    ]

    first = await writer.upsert_passages("doc_1", passages)
    second = await writer.upsert_passages("doc_1", passages)

    assert first.passage_count == 2
    assert second.passage_count == 2
    assert set(await writer.search("Kassenstellen")) == {"psg_index_a"}
    assert set(await writer.search("Spitalsreform")) == {"psg_index_b"}

    engine = create_async_engine(DATABASE_URL or "")
    try:
        async with engine.connect() as connection:
            count = await connection.scalar(
                text("select count(*) from evidence_corpus_indexed_passage")
            )
            manifest = await connection.scalar(
                text("select index_version from evidence_corpus_index_manifest where is_current")
            )
        assert count == 2
        assert manifest == second.index_version
    finally:
        await engine.dispose()


async def test_reverted_passage_leaves_the_index(writer: PostgresIndexWriter) -> None:
    await writer.upsert_passages("doc_2", [_passage("psg_index_c", "Retraktierter Absatz.")])

    await writer.revert_passage("psg_index_c", "retraction")

    assert await writer.search("Retraktierter") == []


async def test_index_rows_carry_provenance_offsets(writer: PostgresIndexWriter) -> None:
    await writer.upsert_passages("doc_3", [_passage("psg_index_d", "Belegter Absatz.")])

    engine = create_async_engine(DATABASE_URL or "")
    try:
        async with engine.connect() as connection:
            row = (
                await connection.execute(
                    text(
                        "select page_from, offset_start, offset_end, speaker_kind "
                        "from evidence_corpus_indexed_passage where passage_id = :id"
                    ),
                    {"id": "psg_index_d"},
                )
            ).one()
        assert row == (3, 0, len("Belegter Absatz."), "institution")
    finally:
        await engine.dispose()
