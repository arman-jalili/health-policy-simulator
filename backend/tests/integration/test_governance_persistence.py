"""Integration: governance violations are append-only and idempotent on retry."""

from __future__ import annotations

import os
from collections.abc import AsyncIterator
from datetime import UTC, datetime

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from governance_compliance.application.dto import ViolationRecord
from governance_compliance.application.values import (
    GuardRuleId,
    InvocationId,
    RunId,
    ViolationClass,
    ViolationId,
)
from governance_compliance.infrastructure.repository.sqlalchemy import SqlAlchemyViolationStore
from shared.config import get_settings

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


@pytest.fixture
async def session_factory(
    migrated: None,
) -> AsyncIterator[async_sessionmaker[AsyncSession]]:
    engine = create_async_engine(DATABASE_URL or "")
    try:
        yield async_sessionmaker(engine, expire_on_commit=False)
    finally:
        await engine.dispose()


async def test_duplicate_retry_writes_exactly_one_violation(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    store = SqlAlchemyViolationStore(session_factory)
    record = ViolationRecord(
        violation_id=ViolationId("vio_retry"),
        run_id=RunId("run_retry"),
        invocation_id=InvocationId("inv_retry"),
        violation_class=ViolationClass.PERSON_NAMED,
        offending_span="Dr. Müller",
        rewritten_span="[person]",
        rule_id=GuardRuleId.GC_001,
        rule_version="GC-001",
        violation_hash="hash_retry_1",
        detected_at=datetime(2026, 11, 6, tzinfo=UTC),
    )

    await store.add(record)
    await store.add(record)

    rows = await SqlAlchemyViolationStore(session_factory).list(run_id=RunId("run_retry"))
    assert len(rows) == 1
    assert rows[0].offending_span == "Dr. Müller"
