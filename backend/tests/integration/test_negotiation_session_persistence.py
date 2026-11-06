"""Integration: a negotiation run and its event log survive a restart (issue #405)."""

from __future__ import annotations

import os

import httpx
import pytest
from alembic import command
from alembic.config import Config

from shared.app import create_app
from shared.config import Settings, get_settings
from shared.enums import AuthMode, Environment, Persistence

DATABASE_URL = os.environ.get("DATABASE_URL") or os.environ.get("HPS_TEST_DATABASE_URL")

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        not DATABASE_URL,
        reason="DATABASE_URL is not set (start compose.yaml and export it)",
    ),
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
        database_url=DATABASE_URL,
        persistence=Persistence.POSTGRES,
        auth_mode=AuthMode.DEMO,
        env=Environment.LOCAL,
    )


async def test_run_and_event_log_survive_engine_dispose(migrated: None) -> None:
    app = create_app(_settings())
    transport = httpx.ASGITransport(app=app, raise_app_exceptions=False)
    async with (
        app.router.lifespan_context(app),
        httpx.AsyncClient(transport=transport, base_url="http://testserver") as client,
    ):
        opened = await client.post(
            "/api/v1/runs", json={"question": "Does this survive?", "round_cap": 2}
        )
        assert opened.status_code == 202, opened.text
        run_id = opened.json()["run_id"]
        round_response = await client.post(f"/api/v1/runs/{run_id}/rounds")
        assert round_response.status_code == 201, round_response.text
    await app.state.db.dispose()

    restarted = create_app(_settings())
    transport = httpx.ASGITransport(app=restarted, raise_app_exceptions=False)
    async with (
        restarted.router.lifespan_context(restarted),
        httpx.AsyncClient(transport=transport, base_url="http://testserver") as client,
    ):
        state = await client.get(f"/api/v1/runs/{run_id}")
        assert state.status_code == 200, state.text
        assert state.json()["round"] == 1
        events = await client.get(f"/api/v1/runs/{run_id}/events")
        assert events.status_code == 200, events.text
        types = [item["event_type"] for item in events.json()["items"]]
        assert types == ["SimulationRunOpened", "RoundOpened"]
    await restarted.state.db.dispose()
