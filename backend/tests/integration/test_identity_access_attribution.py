"""Integration: a command event carries the resolved principal's actor (issue #37).

Requires ``DATABASE_URL`` pointing at PostgreSQL 16 with pgvector (see ``compose.yaml``).
"""

from __future__ import annotations

import os
from types import SimpleNamespace

import httpx
import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import text

from identity_access.infrastructure.resolvers import StaticPrincipalResolver
from identity_access.interfaces.types import ROLE_SCOPES, Principal, Role
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

OPERATOR = Principal(label="operator-1", role=Role.OPERATOR, scopes=ROLE_SCOPES[Role.OPERATOR])


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


async def test_command_event_carries_the_principal_actor() -> None:
    settings = _settings()
    app = create_app(settings)
    app.state.identity_access = SimpleNamespace(
        principal_port=StaticPrincipalResolver({"operator-key": OPERATOR})
    )
    database = Database(settings)
    snapshot_id = ""
    try:
        transport = httpx.ASGITransport(app=app, raise_app_exceptions=False)
        async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
            response = await client.post(
                "/api/v1/corpus/snapshots",
                json={"label": "attribution", "document_ids": []},
                headers={"X-API-Key": "operator-key"},
            )

        assert response.status_code == 201, response.text
        snapshot_id = response.json()["snapshot_id"]

        async with database.session() as session:
            rows = (
                await session.execute(
                    text(
                        "select actor, event_name from shared_event_outbox "
                        "where aggregate_id = :snapshot_id"
                    ),
                    {"snapshot_id": snapshot_id},
                )
            ).all()

        assert rows, "the command must publish at least one event"
        assert all(row.actor == "operator-1" for row in rows)
        assert {row.event_name for row in rows} == {"IndexManifestPublished"}
    finally:
        async with database.session() as session:
            await session.execute(
                text("delete from shared_event_outbox where aggregate_id = :snapshot_id"),
                {"snapshot_id": snapshot_id},
            )
            await session.execute(
                text("delete from evidence_corpus_snapshot where id = :snapshot_id"),
                {"snapshot_id": snapshot_id},
            )
        await database.dispose()
