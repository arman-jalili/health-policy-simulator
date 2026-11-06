"""Integration: EvidenceCorpus wiring proof (issue #26).

Requires ``DATABASE_URL`` pointing at PostgreSQL 16 with pgvector (see ``compose.yaml``).

These tests are the boot-time contract from the module's Wiring Contract: with
``PERSISTENCE=postgres`` the running app must expose SQLAlchemy adapters, ingest through HTTP,
survive a process restart, and write its domain events into the same transaction as the aggregate.
"""

from __future__ import annotations

import asyncio
import os
from datetime import date
from pathlib import Path
from typing import Any

import httpx
import pymupdf
import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from evidence_corpus.application.commands import (
    GetCorpusSnapshotRequest,
    PinCorpusSnapshotRequest,
)
from evidence_corpus.domain.entities import Document, Publication
from evidence_corpus.domain.values import (
    ExtractionMethod,
    ExtractionQuality,
    LanguageTag,
    Offsets,
    SourceType,
    SpeakerKind,
)
from evidence_corpus.infrastructure.events import OutboxEventPublisher
from evidence_corpus.infrastructure.indexing.postgres import PostgresIndexWriter
from evidence_corpus.infrastructure.repository.sqlalchemy import (
    SqlAlchemyArticleRepository,
    SqlAlchemyAuthorityRuleRepository,
    SqlAlchemyCorpusSnapshotRepository,
    SqlAlchemyDocumentRepository,
    SqlAlchemyIngestionRunRepository,
    SqlAlchemyPassageRepository,
)
from shared.app import create_app
from shared.config import Settings, get_settings
from shared.enums import Persistence
from shared.relay import WILDCARD, OutboxRelay

DATABASE_URL = os.environ.get("DATABASE_URL") or os.environ.get("HPS_TEST_DATABASE_URL")

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        not DATABASE_URL,
        reason="DATABASE_URL is not set (start compose.yaml and export it)",
    ),
]

REPOSITORY_TABLES = {
    "evidence_corpus_document",
    "evidence_corpus_publication",
    "evidence_corpus_article",
    "evidence_corpus_passage",
    "evidence_corpus_snapshot",
    "evidence_corpus_snapshot_document",
    "evidence_corpus_ingestion_run",
    "evidence_corpus_indexed_passage",
    "evidence_corpus_index_manifest",
    "shared_event_outbox",
}
BODY = (
    "Die Kassenstellen werden aufgestockt, bestaetigt das Ministerium. "
    "Der gemeinsame Plan sieht eine Reform der Spitalsfinanzierung vor. "
    "Die Laender verhandeln ueber die Verteilung der Mittel. "
) * 4


@pytest.fixture
def alembic_config(monkeypatch: pytest.MonkeyPatch) -> Config:
    monkeypatch.setenv("DATABASE_URL", DATABASE_URL or "")
    get_settings.cache_clear()
    config = Config("alembic.ini")
    config.set_main_option("script_location", "migrations")
    return config


@pytest.fixture(autouse=True)
def migrated(alembic_config: Config) -> None:
    command.upgrade(alembic_config, "head")


def postgres_settings() -> Settings:
    return Settings(
        _env_file=None,
        database_url=DATABASE_URL or "",
        persistence=Persistence.POSTGRES,
    )


def _write_pdf(path: Path) -> Path:
    document = pymupdf.open()  # type: ignore[no-untyped-call]
    page = document.new_page()
    page.insert_textbox(pymupdf.Rect(50, 50, 550, 790), BODY, fontsize=10)  # type: ignore[no-untyped-call]
    document.save(path)  # type: ignore[no-untyped-call]
    document.close()  # type: ignore[no-untyped-call]
    return path


def _document(content_hash: str, outlet: str = "Der Standard") -> Document:
    document = Document.register(
        source_uri=f"file:///tmp/{content_hash}.pdf",
        content_hash=content_hash,
        publication=Publication(outlet=outlet, published_on=date(2026, 10, 1), medium="print"),
        source_type=SourceType.PRESS_REPORT,
        language=LanguageTag("de-AT"),
    )
    document.record_extraction(BODY, ExtractionQuality(ExtractionMethod.NATIVE, 0.99, 0.0))
    article = document.add_article("Kassenstellen", BODY, 1, 1)
    article.add_passage(
        text=BODY[:40],
        offsets=Offsets(0, 40),
        speaker_kind=SpeakerKind.INSTITUTION,
    )
    return document


def _assert_postgres_wiring(app: Any) -> None:
    assert isinstance(app.state.corpus.documents, SqlAlchemyDocumentRepository)
    assert isinstance(app.state.corpus.articles, SqlAlchemyArticleRepository)
    assert isinstance(app.state.corpus.passages, SqlAlchemyPassageRepository)
    assert isinstance(app.state.corpus.ingestion_runs, SqlAlchemyIngestionRunRepository)
    assert isinstance(app.state.corpus.snapshots, SqlAlchemyCorpusSnapshotRepository)
    assert isinstance(app.state.corpus.authority_rules, SqlAlchemyAuthorityRuleRepository)
    assert isinstance(app.state.corpus.events, OutboxEventPublisher)
    assert isinstance(app.state.corpus.index_writer, PostgresIndexWriter)
    assert app.state.corpus.unit_of_work is not None
    assert "/api/v1/documents/{document_id}" in app.openapi()["paths"]


async def _cleanup(settings: Settings, document_ids: list[str]) -> None:
    from shared.db import Database

    database = Database(settings)
    try:
        async with database.session() as session:
            for document_id in document_ids:
                await session.execute(
                    text("delete from shared_event_outbox where aggregate_id = :id"),
                    {"id": document_id},
                )
                await session.execute(
                    text("delete from evidence_corpus_document where id = :id"),
                    {"id": document_id},
                )
    finally:
        await database.dispose()


def test_boot_wiring_and_restart_round_trip(tmp_path: Path) -> None:
    settings = postgres_settings()
    source = _write_pdf(tmp_path / "source.pdf")

    async def scenario() -> None:
        app = create_app(settings)
        _assert_postgres_wiring(app)
        document_ids: list[str] = []
        try:
            transport = httpx.ASGITransport(app=app, raise_app_exceptions=False)
            async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.post(
                    "/api/v1/corpus/documents",
                    json={
                        "source_uri": str(source),
                        "publication": {
                            "outlet": "Der Standard",
                            "published_on": "2026-10-01",
                            "medium": "print",
                        },
                        "source_type": "press_report",
                    },
                )
            assert response.status_code == 202, response.text
            body = response.json()
            assert body["citable"] is False  # no passages until segment + index
            document_id = body["document_id"]
            document_ids.append(document_id)

            # The event was written inside the request transaction, not by a background job.
            async with app.state.db.session() as session:
                names = list(
                    await session.scalars(
                        text(
                            "select event_name from shared_event_outbox "
                            "where aggregate_id = :id order by sequence"
                        ).bindparams(id=document_id)
                    )
                )
            assert "DocumentIngested" in names

            # Articles and passages are aggregate state; add them through the wired repository.
            container = app.state.corpus
            async with container.transaction():
                document = await container.documents.get(document_id)
                assert document is not None
                assert document.articles == []
                source_text = document.extracted_text
                assert source_text is not None
                assert len(source_text) > 40
                article = document.add_article("Kassenstellen", source_text, 1, 1)
                passage_text = source_text[:40]
                passage = article.add_passage(
                    text=passage_text,
                    offsets=Offsets(0, 40),
                    speaker_kind=SpeakerKind.INSTITUTION,
                )
                await container.documents.save(document)
                await container.events.publish(document.drain_events(), actor="test")
            article_id, passage_id = article.id, passage.id

            # A new app object is a new process composition: new engine, new container.
            restarted = create_app(settings)
            _assert_postgres_wiring(restarted)
            try:
                restarted_transport = httpx.ASGITransport(restarted)
                async with httpx.AsyncClient(
                    transport=restarted_transport, base_url="http://test"
                ) as client:
                    document_response = await client.get(f"/api/v1/documents/{document_id}")
                    passage_response = await client.get(f"/api/v1/passages/{passage_id}")

                assert document_response.status_code == 200, document_response.text
                document_body = document_response.json()
                assert document_body["document_id"] == document_id
                assert document_body["source_type"] == "press_report"
                assert document_body["articles"][0]["article_id"] == article_id
                assert document_body["articles"][0]["passage_count"] == 1

                assert passage_response.status_code == 200, passage_response.text
                passage_body = passage_response.json()
                assert passage_body["text"] == passage_text
                assert passage_body["text"] == source_text[0:40]
                assert passage_body["provenance"]["offsets"] == {"start": 0, "end": 40}
                assert passage_body["provenance"]["page_from"] == 1
                assert passage_body["provenance"]["outlet"] == "Der Standard"
                assert passage_body["provenance"]["source_uri"] == str(source)
            finally:
                await restarted.state.db.dispose()
        finally:
            await app.state.db.dispose()
            await _cleanup(settings, document_ids)

    asyncio.run(scenario())


def test_aggregate_write_and_outbox_event_roll_back_together() -> None:
    settings = postgres_settings()
    document = _document(content_hash="sha256:rollback-proof")

    async def scenario() -> None:
        app = create_app(settings)
        container = app.state.corpus
        try:
            with pytest.raises(RuntimeError, match="simulated failure"):
                await _failing_transaction(container, document)

            async with app.state.db.session() as session:
                stored = await session.scalar(
                    text("select count(*) from evidence_corpus_document where id = :id").bindparams(
                        id=document.id
                    )
                )
                events = await session.scalar(
                    text(
                        "select count(*) from shared_event_outbox where aggregate_id = :id"
                    ).bindparams(id=document.id)
                )
            assert stored == 0
            assert events == 0
        finally:
            await app.state.db.dispose()

    asyncio.run(scenario())


async def _failing_transaction(container: Any, document: Document) -> None:
    async with container.transaction():
        await container.documents.save(document)
        await container.events.publish(document.drain_events(), actor="test")
        raise RuntimeError("simulated failure")


def test_outbox_relay_dispatches_each_row_once() -> None:
    settings = postgres_settings()
    document = _document(content_hash="sha256:relay-proof")

    async def scenario() -> None:
        app = create_app(settings)
        database = app.state.db
        received: list[str] = []
        try:
            async with database.session() as session:
                await session.execute(text("delete from shared_event_outbox"))

            async with app.state.corpus.transaction():
                await app.state.corpus.documents.save(document)
                await app.state.corpus.events.publish(document.drain_events(), actor="test")

            relay = OutboxRelay(database.session_factory)

            async def collect(event: Any) -> None:
                received.append(event.event_id)

            relay.subscribe(WILDCARD, collect)

            assert await relay.dispatch_once() == 3
            assert await relay.dispatch_once() == 0
            assert len(received) == 3
            assert len(set(received)) == 3

            async with database.session() as session:
                statuses = list(
                    await session.scalars(text("select status from shared_event_outbox"))
                )
            assert statuses == ["dispatched"] * 3
        finally:
            await database.dispose()
            await _cleanup(settings, [document.id])

    asyncio.run(scenario())


def test_snapshot_manifest_survives_a_second_ingestion() -> None:
    settings = postgres_settings()
    first = _document(content_hash="sha256:snapshot-first")
    second = _document(content_hash="sha256:snapshot-second", outlet="Die Presse")

    async def scenario() -> None:
        app = create_app(settings)
        container = app.state.corpus
        try:
            async with container.transaction():
                await container.documents.save(first)
                await container.events.publish(first.drain_events(), actor="test")

            pinned = await container.pin_corpus_snapshot.execute(
                PinCorpusSnapshotRequest(label="before-second", document_ids=[first.id])
            )

            async with container.transaction():
                await container.documents.save(second)
                await container.events.publish(second.drain_events(), actor="test")

            snapshot = await container.get_corpus_snapshot.execute(
                GetCorpusSnapshotRequest(snapshot_id=pinned.snapshot_id)
            )
            assert snapshot.document_ids == [first.id]
            assert snapshot.manifest_hash == pinned.manifest_hash
            assert await container.snapshots.list_document_ids(pinned.snapshot_id) == [first.id]
        finally:
            async with app.state.db.session() as session:
                await session.execute(
                    text("delete from evidence_corpus_snapshot where label = 'before-second'")
                )
            await app.state.db.dispose()
            await _cleanup(settings, [first.id, second.id])

    asyncio.run(scenario())


def test_alembic_round_trip_creates_every_repository_table(
    alembic_config: Config,
) -> None:
    url = DATABASE_URL or ""
    command.downgrade(alembic_config, "base")
    assert REPOSITORY_TABLES.isdisjoint(asyncio.run(_table_names(url)))

    command.upgrade(alembic_config, "head")
    assert asyncio.run(_table_names(url)) >= REPOSITORY_TABLES

    command.downgrade(alembic_config, "base")
    assert REPOSITORY_TABLES.isdisjoint(asyncio.run(_table_names(url)))

    command.upgrade(alembic_config, "head")
    assert asyncio.run(_table_names(url)) >= REPOSITORY_TABLES


async def _table_names(url: str) -> set[str]:
    engine = create_async_engine(url)
    try:
        async with engine.connect() as connection:
            result = await connection.execute(
                text(
                    "select table_name from information_schema.tables where table_schema = 'public'"
                )
            )
            return {row[0] for row in result}
    finally:
        await engine.dispose()
