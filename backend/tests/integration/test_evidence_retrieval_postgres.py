"""Integration: pack assembly works under PERSISTENCE=postgres (issue #411)."""

from __future__ import annotations

import os
from datetime import date
from typing import Any

import httpx
import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import text

from evidence_corpus.domain.entities import Document, Publication
from evidence_corpus.domain.values import (
    ExtractionMethod,
    ExtractionQuality,
    LanguageTag,
    Offsets,
    SourceType,
    SpeakerKind,
)
from shared.app import create_app
from shared.config import Settings, get_settings
from shared.enums import Persistence

DATABASE_URL = os.environ.get("DATABASE_URL") or os.environ.get("HPS_TEST_DATABASE_URL")
pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(not DATABASE_URL, reason="DATABASE_URL is not set"),
]
BODY = "Die Kassenstellen werden ausgebaut, bestaetigt die Gesundheitskasse. " * 4


def _settings() -> Settings:
    return Settings(
        _env_file=None,
        database_url=DATABASE_URL or "",
        persistence=Persistence.POSTGRES,
    )


@pytest.fixture(scope="module")
def migrated() -> None:
    os.environ.setdefault("DATABASE_URL", DATABASE_URL or "")
    get_settings.cache_clear()
    config = Config("alembic.ini")
    config.set_main_option("script_location", "migrations")
    command.upgrade(config, "head")


def _document() -> Document:
    document = Document.register(
        source_uri="file:///tmp/postgres-retrieval.pdf",
        content_hash="sha256:postgres-retrieval-411",
        publication=Publication(
            outlet="Der Standard", published_on=date(2026, 10, 1), medium="print"
        ),
        source_type=SourceType.OFFICIAL_STATISTICS,
        language=LanguageTag("de-AT"),
    )
    document.record_extraction(BODY, ExtractionQuality(ExtractionMethod.NATIVE, 0.99, 0.0))
    article = document.add_article("Kassenstellen", BODY, 1, 1)
    article.add_passage(
        text=BODY[:70],
        offsets=Offsets(0, 70),
        speaker_kind=SpeakerKind.INSTITUTION,
    )
    return document


async def test_pack_assembly_resolves_citable_passages_in_the_postgres_family(
    migrated: None,
) -> None:
    app = create_app(_settings())
    document = _document()
    try:
        container = app.state.corpus
        async with container.transaction():
            await container.documents.save(document)
        await container.index_ingested_passages.execute(
            __import__(
                "evidence_corpus.application.commands", fromlist=["IndexIngestedPassagesRequest"]
            ).IndexIngestedPassagesRequest(document_id=document.id)
        )
        snapshot = await container.pin_corpus_snapshot.execute(
            __import__(
                "evidence_corpus.application.commands", fromlist=["PinCorpusSnapshotRequest"]
            ).PinCorpusSnapshotRequest(label="postgres-retrieval-411", document_ids=[document.id])
        )

        transport = httpx.ASGITransport(app=app, raise_app_exceptions=False)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/api/v1/evidence/packs",
                json={
                    "claim": "Kassenstellen werden ausgebaut",
                    "claim_type": "quantitative",
                    "snapshot_id": snapshot.snapshot_id,
                },
            )
        assert response.status_code == 201, response.text
        body: Any = response.json()
        assert body["candidates"], body
        passage_id = body["candidates"][0]["passage_id"]

        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            citation = await client.get(f"/api/v1/passages/{passage_id}")
        assert citation.status_code == 200, citation.text
        assert citation.json()["passage_id"] == passage_id
    finally:
        async with app.state.db.session() as session:
            await session.execute(
                text("delete from evidence_corpus_document where id = :id"),
                {"id": document.id},
            )
            await session.execute(
                text("delete from evidence_corpus_snapshot where id = :id"),
                {"id": snapshot.snapshot_id},
            )
        await app.state.db.dispose()
