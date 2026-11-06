"""E2E: consensus-analysis is mounted and fails closed through the public API (issue #321).

Canonical: ``.pi/architecture/modules/consensus-analysis.md`` (Wiring Contract)

Two things are proved here, and only one of them is about a happy path. The reads answer from the
projection — empty before any run closes, which is the honest answer. The derivations refuse with a
named reason, because the run log and the mandate threshold are not published at runtime yet; an
empty agenda or a default quorum would manufacture agreement, which is the failure this context
exists to prevent.
"""

from __future__ import annotations

import httpx
from fastapi import FastAPI

from shared.app import create_app
from shared.config import Settings
from shared.enums import Persistence

DATABASE_URL = "postgresql+asyncpg://hps:hps@localhost:5433/health_policy"


def _app() -> FastAPI:
    return create_app(
        Settings(_env_file=None, database_url=DATABASE_URL, persistence=Persistence.MEMORY)
    )


async def test_the_router_is_mounted_at_the_frozen_paths() -> None:
    app = _app()
    paths = set(app.openapi()["paths"])
    await app.state.db.dispose()

    assert "/api/v1/runs/{run_id}/consensus" in paths
    assert "/api/v1/runs/{run_id}/analysis:derive" in paths
    assert "/api/v1/runs/{run_id}/conflicts/open" in paths
    assert "/api/v1/runs/{run_id}/packages" in paths
    assert "/api/v1/packages/{package_id}/scenarios" in paths
    assert "/api/v1/packages/{package_id}/comparison" in paths


async def test_reading_the_projection_of_a_run_that_never_closed_is_empty_not_an_error() -> None:
    app = _app()
    transport = httpx.ASGITransport(app=app, raise_app_exceptions=False)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        consensus = await client.get("/api/v1/runs/run_e2e_none/consensus")
        conflicts = await client.get("/api/v1/runs/run_e2e_none/conflicts/open")
        packages = await client.get("/api/v1/runs/run_e2e_none/packages")
    await app.state.db.dispose()

    assert consensus.status_code == 200, consensus.text
    assert consensus.json() == {"records": []}
    assert conflicts.status_code == 200, conflicts.text
    assert conflicts.json() == {"conflicts": []}
    assert packages.status_code == 200, packages.text
    assert packages.json() == {"packages": []}


async def test_deriving_without_a_run_log_fails_closed_with_a_named_reason() -> None:
    app = _app()
    transport = httpx.ASGITransport(app=app, raise_app_exceptions=False)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.post(
            "/api/v1/runs/run_e2e_none/analysis:derive", json={"topics": []}
        )
    await app.state.db.dispose()

    assert response.status_code == 503, response.text
    body = response.json()
    assert body["code"] == "CONSENSUS_ANALYSIS_UNAVAILABLE"
    assert "no mandate" in body["message"]
    assert "default quorum" in body["message"]


async def test_deriving_is_refused_before_a_default_threshold_could_be_used() -> None:
    app = _app()
    transport = httpx.ASGITransport(app=app, raise_app_exceptions=False)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.post("/api/v1/runs/run_e2e_none/analysis:derive", json={})
    await app.state.db.dispose()

    assert response.status_code == 503
    body = response.json()
    assert body["code"] == "CONSENSUS_ANALYSIS_UNAVAILABLE"
    assert body["trace_id"]
