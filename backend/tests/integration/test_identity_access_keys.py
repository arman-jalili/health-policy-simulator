"""Integration: hashed key store against PostgreSQL (issue #36).

Requires ``DATABASE_URL`` pointing at PostgreSQL 16 with pgvector (see ``compose.yaml``).
"""

from __future__ import annotations

import os

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import delete

from identity_access.infrastructure.key_resolver import KeyResolver
from identity_access.infrastructure.key_store import HashedApiKeyStore
from identity_access.infrastructure.keys import Sha256ApiKeyFactory, hash_key
from identity_access.infrastructure.repository.models import ApiKeyRow
from identity_access.infrastructure.repository.sqlalchemy import SqlAlchemyApiKeyRepository
from identity_access.interfaces.dto import CreateApiKeyCommand
from identity_access.interfaces.types import Role
from shared.config import Settings, get_settings
from shared.db import Database
from shared.enums import Persistence

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
    return Config("alembic.ini")


@pytest.fixture(autouse=True)
def migrated(alembic_config: Config) -> None:
    command.upgrade(alembic_config, "head")


def _settings() -> Settings:
    return Settings(
        _env_file=None,
        database_url=DATABASE_URL or "",
        persistence=Persistence.POSTGRES,
    )


async def test_key_is_hashed_at_rest_and_plaintext_is_returned_once() -> None:
    settings = _settings()
    database = Database(settings)
    key_id = ""
    issued_key = ""
    try:
        async with database.session() as session:
            store = HashedApiKeyStore(SqlAlchemyApiKeyRepository(session), Sha256ApiKeyFactory())
            issued = await store.create_key(CreateApiKeyCommand(label="ops", role=Role.OPERATOR))
            key_id, issued_key = issued.key_id, issued.key
            row = await session.get(ApiKeyRow, issued.key_id)

        assert row is not None
        assert row.key_hash != issued_key
        assert issued_key.split(".", 1)[1] not in row.key_hash
        assert row.key_hash == hash_key(issued_key.split(".", 1)[1], row.salt)

        async with database.session() as session:
            store = HashedApiKeyStore(SqlAlchemyApiKeyRepository(session), Sha256ApiKeyFactory())
            principal = await KeyResolver(store).resolve(issued_key)
            assert principal.role is Role.OPERATOR
            await store.revoke_key(key_id)

        async with database.session() as session:
            store = HashedApiKeyStore(SqlAlchemyApiKeyRepository(session), Sha256ApiKeyFactory())
            assert await store.lookup(issued_key) is None
    finally:
        async with database.session() as session:
            await session.execute(delete(ApiKeyRow).where(ApiKeyRow.key_id == key_id))
        await database.dispose()
