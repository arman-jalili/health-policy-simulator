"""Integration: a closed run with no stances is a domain outcome, not an outage (#413)."""

from __future__ import annotations

from collections.abc import AsyncIterator

import httpx
import pytest
from fastapi import FastAPI

from consensus_analysis.infrastructure.sources import UnavailableRunLog
from shared.app import create_app
from shared.config import Settings
from shared.demo_seed import seed_demo
from shared.enums import AuthMode, Persistence

DATABASE_URL = "postgresql+asyncpg://hps:hps@localhost:5433/health_policy"


def _app() -> FastAPI:
    return create_app(
        Settings(
            _env_file=None,
            database_url=DATABASE_URL,
            persistence=Persistence.MEMORY,
            auth_mode=AuthMode.DEMO,
        )
    )


@pytest.fixture
async def client() -> AsyncIterator[tuple[FastAPI, httpx.AsyncClient]]:
    app = _app()
    transport = httpx.ASGITransport(app=app, raise_app_exceptions=False)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as http_client:
        yield app, http_client
    await app.state.db.dispose()


async def _closed_abstained_run(client: httpx.AsyncClient) -> str:
    opened = await client.post(
        "/api/v1/runs",
        json={
            "question": "Niemand nimmt Stellung",
            "round_cap": 1,
            "stakeholder_ids": ["stk_aerztekammer"],
        },
    )
    assert opened.status_code == 202, opened.text
    run_id = str(opened.json()["run_id"])
    assert (await client.post(f"/api/v1/runs/{run_id}/rounds")).status_code == 201
    abstained = await client.post(
        f"/api/v1/runs/{run_id}/abstentions",
        json={"stakeholder_id": "stk_aerztekammer", "topic": "Niemand nimmt Stellung"},
    )
    assert abstained.status_code == 204
    closed = await client.post(
        f"/api/v1/runs/{run_id}/rounds/1:close",
        json={"learning": [], "convergence": "none"},
    )
    assert closed.status_code == 200, closed.text
    return run_id


async def test_zero_stances_returns_unresolved_with_a_named_reason(
    client: tuple[FastAPI, httpx.AsyncClient],
) -> None:
    _, http_client = client
    run_id = await _closed_abstained_run(http_client)

    derived = await http_client.post(f"/api/v1/runs/{run_id}/analysis:derive", json={})

    assert derived.status_code == 200, derived.text
    records = derived.json()["records"]
    assert len(records) == 1
    assert records[0]["outcome"] == "unresolved"
    assert records[0]["support"] == 0.0
    assert records[0]["reason"] == "no_recorded_stances"


async def test_stances_still_derive_consensus(
    client: tuple[FastAPI, httpx.AsyncClient],
) -> None:
    app, http_client = client
    seed = await seed_demo(app)
    opened = await http_client.post(
        "/api/v1/runs",
        json={
            "question": "Kassenstellen sichern",
            "round_cap": 1,
            "stakeholder_ids": ["stk_aerztekammer"],
        },
    )
    run_id = str(opened.json()["run_id"])
    assert (await http_client.post(f"/api/v1/runs/{run_id}/rounds")).status_code == 201
    position = await http_client.post(
        f"/api/v1/runs/{run_id}/positions",
        json={
            "stakeholder_id": "stk_aerztekammer",
            "topic": "Kassenstellen",
            "stance": "support",
            "proposal": {"summary": "Kassenstellen ausbauen"},
            "evidence_ids": [seed.pack_ids["kassenstellen"]],
        },
    )
    assert position.status_code == 201, position.text
    turn = await http_client.post(
        f"/api/v1/runs/{run_id}/turns",
        json={
            "stakeholder_id": "stk_aerztekammer",
            "target": {"topic": "Kassenstellen"},
            "stance": "support",
            "text": "Das ASVG regelt die Kassenstellen und die Finanzierung.",
            "claims": [{"text": "Das ASVG regelt die Kassenstellen."}],
            "evidence_ids": [seed.pack_ids["kassenstellen"]],
            "invocation_id": "inv_consensus",
        },
    )
    assert turn.status_code == 201, turn.text
    closed = await http_client.post(
        f"/api/v1/runs/{run_id}/rounds/1:close",
        json={"learning": [], "convergence": "none"},
    )
    assert closed.status_code == 200, closed.text

    derived = await http_client.post(f"/api/v1/runs/{run_id}/analysis:derive", json={})

    assert derived.status_code == 200, derived.text
    record = derived.json()["records"][0]
    assert record["outcome"] == "consensus"
    assert record["support"] == 1.0
    assert record["reason"] is None


async def test_unbound_log_still_reports_the_dependency_as_unavailable(
    client: tuple[FastAPI, httpx.AsyncClient],
) -> None:
    app, http_client = client
    run_id = await _closed_abstained_run(http_client)
    app.state.consensus_analysis.derive_consensus._log = UnavailableRunLog()

    derived = await http_client.post(f"/api/v1/runs/{run_id}/analysis:derive", json={})

    assert derived.status_code == 503, derived.text
    assert derived.json()["code"] == "CONSENSUS_ANALYSIS_UNAVAILABLE"
    assert "run-log read model" in derived.json()["message"]
