"""Integration: both SSE feeds are reachable and served by their own context (#420)."""

from __future__ import annotations

import httpx
from fastapi import FastAPI

from shared.app import create_app
from shared.config import Settings
from shared.enums import AuthMode, Persistence
from tests.conftest import TEST_DATABASE_URL


def _app() -> FastAPI:
    return create_app(
        Settings(
            _env_file=None,
            database_url=TEST_DATABASE_URL,
            persistence=Persistence.MEMORY,
            auth_mode=AuthMode.DEMO,
        )
    )


async def test_each_sse_path_is_served_by_its_own_router() -> None:
    app = _app()
    transport = httpx.ASGITransport(app=app, raise_app_exceptions=False)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        orchestration = await client.get(
            "/api/v1/runs/run_missing/stream", headers={"Last-Event-ID": "abc"}
        )
        negotiation = await client.get(
            "/api/v1/runs/run_missing/negotiation/stream", headers={"Last-Event-ID": "abc"}
        )
    await app.state.db.dispose()

    assert orchestration.status_code == 400
    assert orchestration.json()["code"] == "UNKNOWN_LAST_EVENT_ID"
    assert negotiation.status_code == 400
    assert negotiation.json()["code"] == "BAD_REQUEST"
    assert "invalid Last-Event-ID" in negotiation.json()["message"]
