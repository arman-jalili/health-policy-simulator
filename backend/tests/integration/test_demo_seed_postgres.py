"""Integration: demo seeding is idempotent against PostgreSQL (#414)."""

from __future__ import annotations

import os

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import text

from shared.app import create_app
from shared.config import Settings, get_settings
from shared.demo_seed import seed_demo
from shared.enums import Persistence

DATABASE_URL = os.environ.get("DATABASE_URL") or os.environ.get("HPS_TEST_DATABASE_URL")
pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(not DATABASE_URL, reason="DATABASE_URL is not set"),
]


@pytest.fixture(scope="module")
def migrated() -> None:
    os.environ.setdefault("DATABASE_URL", DATABASE_URL or "")
    get_settings.cache_clear()
    config = Config("alembic.ini")
    config.set_main_option("script_location", "migrations")
    command.upgrade(config, "head")


def _settings() -> Settings:
    return Settings(
        _env_file=None,
        database_url=DATABASE_URL or "",
        persistence=Persistence.POSTGRES,
    )


async def test_second_seed_creates_no_duplicate_document_snapshot_figure_or_pack(
    migrated: None,
) -> None:
    app = create_app(_settings())
    try:
        first = await seed_demo(app)
        second = await seed_demo(app)
        assert first.document_id == second.document_id
        assert first.snapshot_id == second.snapshot_id
        assert first.pack_ids == second.pack_ids
        assert len(first.figure_ids) == 5
        assert sorted(first.figure_ids) == sorted(second.figure_ids)
    finally:
        async with app.state.db.session() as session:
            await session.execute(
                text("delete from shared_event_outbox where aggregate_id = :id"),
                {"id": first.document_id},
            )
            await session.execute(
                text("delete from evidence_corpus_document where id = :id"),
                {"id": first.document_id},
            )
            await session.execute(
                text("delete from evidence_corpus_snapshot where id = :id"),
                {"id": first.snapshot_id},
            )
            for pack_id in first.pack_ids.values():
                await session.execute(
                    text("delete from evidence_retrieval_pack where id = :id"), {"id": pack_id}
                )
            await session.execute(
                text(
                    "delete from claim_validation_reference_figure where source_id = 'demo-corpus'"
                )
            )
        await app.state.db.dispose()
