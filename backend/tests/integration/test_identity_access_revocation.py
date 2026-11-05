"""Integration: revocation is visible on the very next request (issue #39).

Requires ``DATABASE_URL`` pointing at PostgreSQL 16 with pgvector (see ``compose.yaml``).
"""

from __future__ import annotations

import os
from types import SimpleNamespace

import httpx
import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import delete

from identity_access.infrastructure.key_resolver import KeyResolver
from identity_access.infrastructure.key_store import HashedApiKeyStore
from identity_access.infrastructure.keys import Sha256ApiKeyFactory
from identity_access.infrastructure.repository.models import ApiKeyRow
from identity_access.infrastructure.repository.sqlalchemy import SqlAlchemyApiKeyRepository
from identity_access.interfaces.dto import CreateApiKeyCommand
from identity_access.interfaces.http.router import router as admin_router
from identity_access.interfaces.types import Role
from shared.app import create_app
from shared.config import Settings, get_settings
from shared.db import Database
from shared.enums import AuthMode, Persistence

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
        auth_mode=AuthMode.STRICT,
    )


async def test_revoked_key_is_rejected_on_the_next_request() -> None:
    settings = _settings()
    database = Database(settings)
    app = create_app(settings)
    app.include_router(admin_router)
    key_ids: list[str] = []
    try:
        async with database.session() as session:
            store = HashedApiKeyStore(SqlAlchemyApiKeyRepository(session), Sha256ApiKeyFactory())
            admin_key = await store.create_key(
                CreateApiKeyCommand(label="admin-1", role=Role.ADMIN)
            )
            key_ids.append(admin_key.key_id)
            app.state.identity_access = SimpleNamespace(
                principal_port=KeyResolver(store),
                api_key_admin=store,
            )
            transport = httpx.ASGITransport(app=app, raise_app_exceptions=False)
            async with httpx.AsyncClient(
                transport=transport, base_url="http://testserver"
            ) as client:
                admin_headers = {"X-API-Key": admin_key.key}

                created = await client.post(
                    "/api/v1/admin/keys",
                    json={"label": "ops", "role": "operator"},
                    headers=admin_headers,
                )
                assert created.status_code == 201, created.text
                issued = created.json()
                key_ids.append(issued["key_id"])
                issued_headers = {"X-API-Key": issued["key"]}

                listed = await client.get("/api/v1/admin/keys", headers=admin_headers)
                assert listed.status_code == 200, listed.text
                assert {row["key_id"] for row in listed.json()} >= {issued["key_id"]}

                allowed = await client.get("/api/v1/corpus/authority-rules", headers=issued_headers)
                assert allowed.status_code == 200, allowed.text

                revoked = await client.delete(
                    f"/api/v1/admin/keys/{issued['key_id']}", headers=admin_headers
                )
                assert revoked.status_code == 204, revoked.text

                denied = await client.get("/api/v1/corpus/authority-rules", headers=issued_headers)
                assert denied.status_code == 401, denied.text
                assert denied.json()["code"] == "UNAUTHENTICATED"
    finally:
        async with database.session() as session:
            if key_ids:
                await session.execute(delete(ApiKeyRow).where(ApiKeyRow.key_id.in_(key_ids)))
        await app.state.db.dispose()
        await database.dispose()
