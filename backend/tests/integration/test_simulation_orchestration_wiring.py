"""Integration proof: SimulationOrchestration is mounted, worker-started and streaming."""

from __future__ import annotations

import asyncio

import httpx
import pytest

from shared.app import create_app
from shared.config import Settings
from shared.enums import AuthMode, Persistence
from simulation_orchestration.application.errors import UnknownModel
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


async def test_usage_endpoint_returns_zero_usage_for_bootstrap_run() -> None:
    app = create_app(_settings())
    transport = httpx.ASGITransport(app=app, raise_app_exceptions=False)
    async with (
        app.router.lifespan_context(app),
        httpx.AsyncClient(transport=transport, base_url="http://testserver") as client,
    ):
        await client.post("/api/v1/runs/run_2:start", json={})
        usage = await client.get("/api/v1/runs/run_2/usage")
        assert usage.status_code == 200, usage.text
        assert usage.json()["total_invocations"] == 0
        assert usage.json()["cost"] == "0"


def test_unknown_configured_model_fails_at_boot() -> None:
    with pytest.raises(UnknownModel, match="configured model"):
        create_app(_settings(simulation_model_id="missing-model"))
