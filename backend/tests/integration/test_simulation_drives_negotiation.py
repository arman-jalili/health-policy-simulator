"""Integration: starting a simulation actually drives the negotiation run (#415)."""

from __future__ import annotations

import asyncio

import httpx
from fastapi import FastAPI

from shared.app import create_app
from shared.config import Settings
from shared.demo_seed import seed_demo
from shared.enums import AuthMode, Persistence
from tests.conftest import TEST_DATABASE_URL


def _app(**overrides: object) -> FastAPI:
    values: dict[str, object] = {
        "_env_file": None,
        "database_url": TEST_DATABASE_URL,
        "persistence": Persistence.MEMORY,
        "auth_mode": AuthMode.DEMO,
    }
    values.update(overrides)
    return create_app(Settings(**values))  # type: ignore[arg-type]


async def _open_run(client: httpx.AsyncClient, question: str = "Kassenstellen sichern") -> str:
    opened = await client.post(
        "/api/v1/runs",
        json={"question": question, "round_cap": 1, "stakeholder_ids": ["stk_aerztekammer"]},
    )
    assert opened.status_code == 202, opened.text
    return str(opened.json()["run_id"])


async def _wait_for_job(
    client: httpx.AsyncClient, job_id: str, terminal: set[str]
) -> dict[str, object]:
    for _ in range(500):
        response = await client.get(f"/api/v1/jobs/{job_id}")
        assert response.status_code == 200, response.text
        job = dict(response.json())
        if job["status"] in terminal:
            return job
        await asyncio.sleep(0.02)
    raise AssertionError(f"job {job_id} did not reach {terminal}")


async def test_simulation_produces_rounds_positions_arguments_and_a_closed_run() -> None:
    app = _app()
    assert (
        type(app.state.simulation_orchestration.run_simulation_job._negotiation).__name__
        == "NegotiationSessionGateway"
    )
    await seed_demo(app)
    transport = httpx.ASGITransport(app=app, raise_app_exceptions=False)
    async with (
        app.router.lifespan_context(app),
        httpx.AsyncClient(transport=transport, base_url="http://testserver") as client,
    ):
        opened = await client.post(
            "/api/v1/runs",
            json={
                "question": "Kassenstellen und Versorgung",
                "round_cap": 2,
                "stakeholder_ids": ["stk_aerztekammer"],
            },
        )
        run_id = str(opened.json()["run_id"])
        started = await client.post(f"/api/v1/runs/{run_id}:start", json={})
        job = await _wait_for_job(client, str(started.json()["job_id"]), {"completed"})

        assert job["status"] == "completed"
        state = (await client.get(f"/api/v1/runs/{run_id}")).json()
        assert state["closed"] is True
        rounds = (await client.get(f"/api/v1/runs/{run_id}/rounds")).json()["items"]
        assert len(rounds) == 2
        events = (await client.get(f"/api/v1/runs/{run_id}/events")).json()["items"]
        types = [item["event_type"] for item in events]
        assert "InitialPositionStated" in types
        assert "ArgumentSubmitted" in types
        assert types[-1] == "SimulationRunClosed"

        usage = (await client.get(f"/api/v1/runs/{run_id}/usage")).json()
        assert usage["total_invocations"] == 2
        assert usage["by_stakeholder"][0]["stakeholder"] == "stk_aerztekammer"

        consensus = (await client.get(f"/api/v1/runs/{run_id}/consensus")).json()
        assert consensus["records"]


async def test_configured_prices_show_a_non_zero_cost_for_the_real_stakeholder() -> None:
    app = _app(simulation_input_price_per_1k=1.0, simulation_output_price_per_1k=1.0)
    await seed_demo(app)
    transport = httpx.ASGITransport(app=app, raise_app_exceptions=False)
    async with (
        app.router.lifespan_context(app),
        httpx.AsyncClient(transport=transport, base_url="http://testserver") as client,
    ):
        run_id = await _open_run(client)
        started = await client.post(f"/api/v1/runs/{run_id}:start", json={})
        await _wait_for_job(client, str(started.json()["job_id"]), {"completed"})
        usage = (await client.get(f"/api/v1/runs/{run_id}/usage")).json()

    assert usage["total_invocations"] == 1
    assert float(usage["cost"]) > 0.0
    assert usage["by_stakeholder"][0]["stakeholder"] == "stk_aerztekammer"
    assert float(usage["by_stakeholder"][0]["cost"]) > 0.0


async def test_a_graph_that_cannot_drive_the_run_never_reports_completed() -> None:
    app = _app()  # no seeded corpus, so the gateway cannot assemble an evidence pack
    transport = httpx.ASGITransport(app=app, raise_app_exceptions=False)
    async with (
        app.router.lifespan_context(app),
        httpx.AsyncClient(transport=transport, base_url="http://testserver") as client,
    ):
        opened = await client.post(
            "/api/v1/runs",
            json={"question": "No corpus", "round_cap": 1, "stakeholder_ids": ["stk_aerztekammer"]},
        )
        run_id = str(opened.json()["run_id"])
        started = await client.post(f"/api/v1/runs/{run_id}:start", json={})
        job = await _wait_for_job(client, str(started.json()["job_id"]), {"failed", "dead_letter"})

    assert job["status"] in {"failed", "dead_letter"}
    assert job["status"] != "completed"


async def test_automated_run_does_not_manufacture_unanimity() -> None:
    app = _app()
    await seed_demo(app)
    transport = httpx.ASGITransport(app=app, raise_app_exceptions=False)
    async with (
        app.router.lifespan_context(app),
        httpx.AsyncClient(transport=transport, base_url="http://testserver") as client,
    ):
        ids = [
            item["stakeholder_id"]
            for item in (await client.get("/api/v1/stakeholders")).json()["items"]
        ]
        opened = await client.post(
            "/api/v1/runs",
            json={
                "question": "Kassenstellen und Versorgung",
                "round_cap": 1,
                "stakeholder_ids": ids,
            },
        )
        run_id = str(opened.json()["run_id"])
        started = await client.post(f"/api/v1/runs/{run_id}:start", json={})
        await _wait_for_job(client, str(started.json()["job_id"]), {"completed"})

        records = (await client.get(f"/api/v1/runs/{run_id}/consensus")).json()["records"]
        rounds = (await client.get(f"/api/v1/runs/{run_id}/rounds")).json()["items"]
        events = (await client.get(f"/api/v1/runs/{run_id}/events")).json()["items"]

    assert records
    assert records[0]["support"] < 1.0
    assert records[0]["minorities"]
    assert records[0]["topic"] != "Kassenstellen und Versorgung"
    assert rounds[0]["learning"]["insights"]
    argument_topics = {
        event["payload"]["target"]["topic"]
        for event in events
        if event["event_type"] == "ArgumentSubmitted"
    }
    assert argument_topics == {records[0]["topic"]}
