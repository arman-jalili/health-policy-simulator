"""Integration: ``0000_bootstrap`` applies, reverts and re-applies on a real PostgreSQL.

Requires ``DATABASE_URL`` (or ``HPS_TEST_DATABASE_URL``) pointing at a PostgreSQL 16 instance
with the pgvector extension available — see ``compose.yaml``.
"""

from __future__ import annotations

import asyncio
import os

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from shared.config import get_settings
from shared.outbox import OutboxWriter

DATABASE_URL = os.environ.get("DATABASE_URL") or os.environ.get("HPS_TEST_DATABASE_URL")
EXPECTED_TABLES = {"shared_event_outbox", "shared_audit"}

# Collected and skipped rather than skipped at collection time: a collection-time skip makes
# pytest exit with code 5 ("no tests ran"), which validators report as a test failure.
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


async def _extension_names(url: str) -> set[str]:
    engine = create_async_engine(url)
    try:
        async with engine.connect() as connection:
            result = await connection.execute(text("select extname from pg_extension"))
            return {row[0] for row in result}
    finally:
        await engine.dispose()


def test_bootstrap_migration_round_trip(alembic_config: Config) -> None:
    url = DATABASE_URL or ""

    command.downgrade(alembic_config, "base")
    assert asyncio.run(_table_names(url)).isdisjoint(EXPECTED_TABLES)

    command.upgrade(alembic_config, "head")
    assert asyncio.run(_table_names(url)) >= EXPECTED_TABLES
    assert {"vector", "pg_trgm"} <= asyncio.run(_extension_names(url))

    command.downgrade(alembic_config, "base")
    assert asyncio.run(_table_names(url)).isdisjoint(EXPECTED_TABLES)

    command.upgrade(alembic_config, "head")
    assert asyncio.run(_table_names(url)) >= EXPECTED_TABLES


def test_outbox_row_round_trips_through_the_database(alembic_config: Config) -> None:
    url = DATABASE_URL or ""
    command.upgrade(alembic_config, "head")

    async def _exercise() -> None:
        engine = create_async_engine(url)
        factory = async_sessionmaker(engine, expire_on_commit=False)
        try:
            async with factory() as session:
                event = await OutboxWriter().write(
                    session,
                    event_name="BootstrapVerified",
                    aggregate_type="Bootstrap",
                    aggregate_id="bootstrap_1",
                    payload={"ok": True},
                    actor="system",
                    trace_id="req_bootstrap_test",
                )
                await session.commit()

                result = await session.execute(
                    text(
                        "select payload, status, payload_schema_version "
                        "from shared_event_outbox where id = :id"
                    ),
                    {"id": event.event_id},
                )
                payload, status, payload_schema_version = result.one()
                assert payload == {"ok": True}
                assert status == "pending"
                assert payload_schema_version == 1

                await session.execute(
                    text("delete from shared_event_outbox where id = :id"),
                    {"id": event.event_id},
                )
                await session.commit()
        finally:
            await engine.dispose()

    asyncio.run(_exercise())
