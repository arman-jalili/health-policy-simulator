"""Integration proof: SimulationOrchestration is mounted, worker-started and streaming."""

from __future__ import annotations

import asyncio
from dataclasses import replace
from decimal import Decimal
from typing import Any, cast

import httpx
import pytest

from shared.app import create_app
from shared.config import Settings
from shared.enums import AuthMode, Persistence
from simulation_orchestration.application.errors import UnknownModel
from simulation_orchestration.application.values import GraphState, RunPhase
from tests.conftest import TEST_DATABASE_URL


def _settings(**overrides: object) -> Settings:
    values: dict[str, object] = {
        "_env_file": None,
        "database_url": TEST_DATABASE_URL,
        "persistence": Persistence.MEMORY,
        "auth_mode": AuthMode.DEMO,
    }
    values.update(overrides)
    return Settings(**values)  # type: ignore[arg-type]


async def test_start_emits_progress_without_manual_worker_step() -> None:
    app = create_app(_settings())
    transport = httpx.ASGITransport(app=app, raise_app_exceptions=False)
    async with (
        app.router.lifespan_context(app),
        httpx.AsyncClient(transport=transport, base_url="http://testserver") as client,
    ):
        started = await client.post("/api/v1/runs/run_1:start", json={"budget": {"max_cost": "1"}})
        assert started.status_code == 202, started.text
        job_id = started.json()["job_id"]
        assert started.json()["status"] == "queued"

        job: dict[str, object] = {}
        for _ in range(100):
            fetched = await client.get(f"/api/v1/jobs/{job_id}")
            assert fetched.status_code == 200, fetched.text
            job = fetched.json()
            if job["status"] == "completed":
                break
            await asyncio.sleep(0.02)

        assert job["status"] == "completed"
        checkpoint = job["checkpoint"]
        assert isinstance(checkpoint, dict)
        assert checkpoint["phase"] == "done"
        sequence = job["progress_sequence"]
        assert isinstance(sequence, int)
        assert sequence >= 3

        stream = await client.get("/api/v1/runs/run_1/stream")
        assert stream.status_code == 200, stream.text
        assert stream.headers["content-type"].startswith("text/event-stream")
        assert "event: run.started" in stream.text
        assert "event: run.completed" in stream.text
        assert stream.text.index("event: run.started") < stream.text.index("event: run.completed")

        last_id = stream.text.rsplit("id: ", 1)[1].split("\n", 1)[0]
        replay = await client.get("/api/v1/runs/run_1/stream", headers={"Last-Event-ID": last_id})
        assert replay.status_code == 200, replay.text
        assert replay.text == ""


class _GatedGraph:
    def __init__(self) -> None:
        self.started = asyncio.Event()
        self.release = asyncio.Event()

    def next_node(self, state: GraphState) -> str | None:
        if state.phase is RunPhase.MANDATE:
            return "first"
        if state.phase is RunPhase.ROUNDS:
            return "second"
        return None

    async def step(self, node_name: str, state: GraphState) -> GraphState:
        if node_name == "first":
            self.started.set()
            await self.release.wait()
            return replace(state, phase=RunPhase.ROUNDS, round=state.round + 1)
        return replace(state, phase=RunPhase.DONE, round=state.round + 1)


async def test_pause_and_resume_through_the_public_api() -> None:
    app = create_app(_settings())
    graph = _GatedGraph()
    cast(Any, app.state.simulation_orchestration.run_simulation_job)._graph = graph
    transport = httpx.ASGITransport(app=app, raise_app_exceptions=False)
    async with (
        app.router.lifespan_context(app),
        httpx.AsyncClient(transport=transport, base_url="http://testserver") as client,
    ):
        started = await client.post("/api/v1/runs/run_pause:start", json={})
        assert started.status_code == 202, started.text
        job_id = started.json()["job_id"]
        await asyncio.wait_for(graph.started.wait(), timeout=2)

        paused = await client.post(
            "/api/v1/runs/run_pause:pause", json={"action": "pause", "reason": "operator"}
        )
        assert paused.status_code == 202, paused.text
        assert paused.json()["status"] == "paused"
        graph.release.set()

        for _ in range(100):
            job = (await client.get(f"/api/v1/jobs/{job_id}")).json()
            if job["status"] == "paused":
                break
            await asyncio.sleep(0.02)
        assert job["status"] == "paused"
        assert job["checkpoint"]["phase"] == "rounds"

        resumed = await client.post("/api/v1/runs/run_pause:resume", json={"action": "resume"})
        assert resumed.status_code == 202, resumed.text
        assert resumed.json()["status"] == "queued"

        for _ in range(100):
            job = (await client.get(f"/api/v1/jobs/{job_id}")).json()
            if job["status"] == "completed":
                break
            await asyncio.sleep(0.02)
        assert job["status"] == "completed"

        stream = await client.get("/api/v1/runs/run_pause/stream")
        assert "event: run.paused" in stream.text
        assert "event: run.resumed" in stream.text
        assert stream.text.index("event: run.paused") < stream.text.index("event: run.resumed")


async def test_usage_endpoint_reports_bootstrap_invocations() -> None:
    app = create_app(_settings())
    transport = httpx.ASGITransport(app=app, raise_app_exceptions=False)
    async with (
        app.router.lifespan_context(app),
        httpx.AsyncClient(transport=transport, base_url="http://testserver") as client,
    ):
        started = await client.post("/api/v1/runs/run_2:start", json={})
        job_id = started.json()["job_id"]
        for _ in range(100):
            job = (await client.get(f"/api/v1/jobs/{job_id}")).json()
            if job["status"] == "completed":
                break
            await asyncio.sleep(0.02)
        usage = await client.get("/api/v1/runs/run_2/usage")
        assert usage.status_code == 200, usage.text
        assert usage.json()["total_invocations"] == 2
        assert Decimal(usage.json()["cost"]) == Decimal("0")
        assert job["checkpoint"]["budget_used_invocations"] == 2


async def test_budget_of_one_pauses_and_resume_with_a_raised_budget_completes() -> None:
    app = create_app(_settings())
    transport = httpx.ASGITransport(app=app, raise_app_exceptions=False)
    async with (
        app.router.lifespan_context(app),
        httpx.AsyncClient(transport=transport, base_url="http://testserver") as client,
    ):
        started = await client.post(
            "/api/v1/runs/run_budget:start", json={"budget": {"max_invocations": 1}}
        )
        assert started.status_code == 202, started.text
        job_id = started.json()["job_id"]

        for _ in range(100):
            job = (await client.get(f"/api/v1/jobs/{job_id}")).json()
            if job["status"] == "paused":
                break
            await asyncio.sleep(0.02)
        assert job["status"] == "paused"
        assert "invocations budget exhausted" in job["error"]
        assert job["checkpoint"]["budget_used_invocations"] == 1

        usage = await client.get("/api/v1/runs/run_budget/usage")
        assert usage.json()["total_invocations"] == 1

        stream = await client.get("/api/v1/runs/run_budget/stream")
        assert "event: run.budget_exhausted" in stream.text

        resumed = await client.post(
            "/api/v1/runs/run_budget:resume",
            json={"action": "resume", "budget": {"max_invocations": 2}},
        )
        assert resumed.status_code == 202, resumed.text
        assert resumed.json()["status"] == "queued"

        for _ in range(100):
            job = (await client.get(f"/api/v1/jobs/{job_id}")).json()
            if job["status"] == "completed":
                break
            await asyncio.sleep(0.02)
        assert job["status"] == "completed"
        assert job["checkpoint"]["budget_used_invocations"] == 2
        usage = await client.get("/api/v1/runs/run_budget/usage")
        assert usage.json()["total_invocations"] == 2


def test_unknown_configured_model_fails_at_boot() -> None:
    with pytest.raises(UnknownModel, match="configured model"):
        create_app(_settings(simulation_model_id="missing-model"))
