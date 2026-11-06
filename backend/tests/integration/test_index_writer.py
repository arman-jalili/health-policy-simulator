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
from evidence_corpus.infrastructure.indexing.memory import InMemoryIndexWriter
from evidence_corpus.infrastructure.indexing.postgres import PostgresIndexWriter
from evidence_retrieval.infrastructure.query_rewrite import GermanQueryRewrite
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


# --- issue #140: compound rewrite must work on the real adapter -------------------------------

_COMPOUND_PASSAGES = [
    _passage("psg_naive_140", "Neue Kassenstellen fuer Dermatologie."),
    _passage("psg_contract_140", "Die Kassenvertragsstellen wurden aufgestockt."),
    _passage("psg_kasse_140", "Die Kasse hat keine Stellen mehr."),
    _passage("psg_unrelated_140", "Die Wartezeit auf Facharzttermine sank."),
]

_COMPOUND_IDS = {passage.passage_id for passage in _COMPOUND_PASSAGES}


async def _seed_compound(writer: PostgresIndexWriter) -> InMemoryIndexWriter:
    await writer.upsert_passages("doc_compound_140", _COMPOUND_PASSAGES)
    memory = InMemoryIndexWriter()
    await memory.upsert_passages("doc_compound_140", _COMPOUND_PASSAGES)
    return memory


async def _postgres_ids(writer: PostgresIndexWriter, query: str) -> set[str]:
    return set(await writer.search(query, limit=100)) & _COMPOUND_IDS


async def _memory_ids(memory: InMemoryIndexWriter, query: str) -> set[str]:
    return set(await memory.search(query)) & _COMPOUND_IDS


async def test_facharzttermine_is_found_through_the_rewritten_query(
    writer: PostgresIndexWriter,
) -> None:
    await _seed_compound(writer)
    query = GermanQueryRewrite().rewrite("Facharzttermine")

    assert "psg_unrelated_140" in await _postgres_ids(writer, query.expanded)


async def test_compound_rewrite_finds_hits_a_naive_query_misses(
    writer: PostgresIndexWriter,
) -> None:
    await _seed_compound(writer)
    rewrite = GermanQueryRewrite().rewrite("Kassenstellen")

    naive = await _postgres_ids(writer, "Kassenstellen")
    expanded = await _postgres_ids(writer, rewrite.expanded)

    assert naive == {"psg_naive_140"}
    assert {"psg_contract_140", "psg_kasse_140"} <= expanded
    assert expanded - naive


async def test_memory_and_postgres_adapters_agree_on_every_query_shape(
    writer: PostgresIndexWriter,
) -> None:
    memory = await _seed_compound(writer)
    rewrite = GermanQueryRewrite().rewrite("Kassenstellen")

    for query in ("Kassenstellen", rewrite.expanded, "Spitalsreform", "Weltraumtourismus"):
        assert await _memory_ids(memory, query) == await _postgres_ids(writer, query), query


async def test_rewrite_never_loses_recall_on_the_postgres_adapter(
    writer: PostgresIndexWriter,
) -> None:
    await _seed_compound(writer)

    for claim in ("Kassenstellen", "Facharzttermine", "Kasse"):
        naive = await _postgres_ids(writer, claim)
        expanded = await _postgres_ids(writer, GermanQueryRewrite().rewrite(claim).expanded)
        assert naive <= expanded, claim
