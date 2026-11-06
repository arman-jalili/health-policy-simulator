"""End-to-end proof of the wired identity-access runtime (issues #41/#42, ADR-009).

Requires ``DATABASE_URL`` pointing at PostgreSQL 16 with pgvector (see ``compose.yaml``).

The only setup shortcut is bootstrapping the first admin key through the wired store; every
subsequent step goes through the public HTTP API and the same container the process uses.
"""

from __future__ import annotations

import os

import httpx
import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import delete

from identity_access.infrastructure.repository.models import ApiKeyRow
from identity_access.interfaces.dto import CreateApiKeyCommand
from identity_access.interfaces.types import Role
from shared.app import create_app
from shared.config import Settings, get_settings
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


async def test_wired_identity_access_runs_end_to_end() -> None:
    app = create_app(_settings())
    key_ids: list[str] = []
    try:
        admin_key = await app.state.identity_access.api_key_admin.create_key(
            CreateApiKeyCommand(label="admin-e2e", role=Role.ADMIN)
        )
        key_ids.append(admin_key.key_id)
        admin_headers = {"X-API-Key": admin_key.key}

        transport = httpx.ASGITransport(app=app, raise_app_exceptions=False)
        async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
            liveness = await client.get("/healthz")
            assert liveness.status_code == 200

            readiness = await client.get("/readyz")
            assert readiness.status_code == 200, readiness.text
            assert readiness.json()["checks"]["database"] == "ok"
            assert readiness.json()["checks"]["llm"] == "scripted"

            created = await client.post(
                "/api/v1/admin/keys",
                json={"label": "operator-e2e", "role": "operator"},
                headers=admin_headers,
            )
            assert created.status_code == 201, created.text
            issued = created.json()
            key_ids.append(issued["key_id"])
            operator_headers = {"X-API-Key": issued["key"]}

            corpus_read = await client.get(
                "/api/v1/corpus/authority-rules", headers=operator_headers
            )
            assert corpus_read.status_code == 200, corpus_read.text

            revoked = await client.delete(
                f"/api/v1/admin/keys/{issued['key_id']}", headers=admin_headers
            )
            assert revoked.status_code == 204, revoked.text

            rejected = await client.get("/api/v1/corpus/authority-rules", headers=operator_headers)
            assert rejected.status_code == 401, rejected.text
            assert rejected.json()["code"] == "UNAUTHENTICATED"
    finally:
        async with app.state.db.session() as session:
            if key_ids:
                await session.execute(delete(ApiKeyRow).where(ApiKeyRow.key_id.in_(key_ids)))
        await app.state.db.dispose()
