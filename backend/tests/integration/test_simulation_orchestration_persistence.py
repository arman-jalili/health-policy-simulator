"""Integration: SimulationOrchestration persists jobs, envelopes, progress and prompts (#217)."""

from __future__ import annotations

import asyncio
import os
from collections.abc import AsyncIterator
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import httpx
import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from shared.app import create_app
from shared.config import Settings, get_settings
from shared.demo_seed import seed_demo
from shared.enums import AuthMode, Persistence
from shared.ids import new_id
from simulation_orchestration.application.commands import StreamSimulationProgressRequest
from simulation_orchestration.application.dto import (
    InvocationEnvelope,
    JobRecord,
    ProgressEventView,
)
from simulation_orchestration.application.rules import PromptVersioning
from simulation_orchestration.application.services import StreamSimulationProgress
from simulation_orchestration.application.state import initial_state
from simulation_orchestration.application.values import (
    BudgetUsage,
    InvocationId,
    InvocationOutcome,
    JobId,
    JobStatus,
    ProgressKind,
    PromptRef,
    RunId,
)
from simulation_orchestration.infrastructure.repository.sqlalchemy import (
    SqlAlchemyInvocationStore,
    SqlAlchemyJobStore,
    SqlAlchemyProgressStore,
    SqlAlchemyPromptRegistry,
)

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


@pytest.fixture
async def session_factory(
    migrated: None,
) -> AsyncIterator[async_sessionmaker[AsyncSession]]:
    engine = create_async_engine(DATABASE_URL or "")
    try:
        yield async_sessionmaker(engine, expire_on_commit=False)
    finally:
        await engine.dispose()


async def test_job_invocation_progress_and_prompt_round_trip(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    now = datetime(2026, 11, 6, tzinfo=UTC)
    run_id = RunId(new_id("run"))
    job = JobRecord(
        job_id=JobId(new_id("job")),
        run_id=run_id,
        status=JobStatus.QUEUED,
        attempts=0,
        checkpoint=initial_state(run_id),
        budget_used=BudgetUsage(),
        error=None,
        claimed_by=None,
        created_at=now,
        updated_at=now,
    )
    jobs = SqlAlchemyJobStore(session_factory)
    await jobs.add(job)
    assert await jobs.get(job.job_id) == job
    assert await jobs.get_by_run(run_id) == job

    claimed = await jobs.claim_next("worker-1", now + timedelta(seconds=1))
    assert claimed is not None
    assert claimed.job_id == job.job_id
    assert claimed.status is JobStatus.RUNNING
    assert claimed.attempts == 1
    assert await jobs.claim_next("worker-2", now + timedelta(seconds=2)) is None

    dead = replace(claimed, lease_expires_at=now - timedelta(seconds=1))
    await jobs.save(dead)
    reclaimed = await jobs.claim_next("worker-2", now + timedelta(seconds=3))
    assert reclaimed is not None
    assert reclaimed.claimed_by == "worker-2"
    assert reclaimed.attempts == 2

    invocations = SqlAlchemyInvocationStore(session_factory)
    envelope = InvocationEnvelope(
        invocation_id=InvocationId(new_id("inv")),
        run_id=run_id,
        round=1,
        stakeholder="oegk",
        purpose="take_turn",
        model="scripted-local",
        prompt=PromptRef("take-turn", 1),
        parameters={"temperature": 0},
        evidence_pack_ids=("pack_1",),
        input_tokens=10,
        output_tokens=5,
        cost_estimate=Decimal("0.001"),
        latency_ms=12,
        outcome=InvocationOutcome.SUCCESS,
        created_at=now,
    )
    await invocations.add(envelope)
    await invocations.add(envelope)

    restarted_invocations = SqlAlchemyInvocationStore(session_factory)
    stored = await restarted_invocations.list_for_run(run_id)
    assert [item.invocation_id for item in stored] == [envelope.invocation_id]
    usage = await restarted_invocations.usage_for_run(run_id)
    assert (usage.invocations, usage.input_tokens, usage.output_tokens) == (1, 10, 5)

    progress = SqlAlchemyProgressStore(session_factory)
    event = ProgressEventView(
        event_id=new_id("evt"),
        run_id=run_id,
        sequence=1,
        kind=ProgressKind.STARTED,
        payload={"round": 1},
        created_at=now,
    )
    await progress.append(event)
    restarted_progress = SqlAlchemyProgressStore(session_factory)
    assert await restarted_progress.latest_sequence(run_id) == 1
    assert await restarted_progress.get(event.event_id) == event
    assert await restarted_progress.list_after(run_id, 0, 10) == [event]

    prompts = SqlAlchemyPromptRegistry(session_factory)
    first = PromptVersioning().next_version(existing=[], name=f"policy-{run_id}", body="one")
    second = PromptVersioning().next_version(existing=[first], name=f"policy-{run_id}", body="two")
    await prompts.save(first)
    await prompts.save(second)
    restarted_prompts = SqlAlchemyPromptRegistry(session_factory)
    assert (await restarted_prompts.latest(first.name)).version == 2  # type: ignore[union-attr]
    assert (await restarted_prompts.get(first.name, 1)).body == "one"  # type: ignore[union-attr]


async def test_concurrent_progress_appends_are_gapless_on_postgres(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    now = datetime(2026, 11, 6, tzinfo=UTC)
    run_id = RunId(new_id("run"))
    progress = SqlAlchemyProgressStore(session_factory)

    def event() -> ProgressEventView:
        return ProgressEventView(
            event_id=new_id("evt"),
            run_id=run_id,
            sequence=0,
            kind=ProgressKind.STARTED,
            payload={"concurrent": True},
            created_at=now,
        )

    await asyncio.gather(*(progress.append(event()) for _ in range(10)))

    stored = await progress.list_after(run_id, 0, 100)
    assert [item.sequence for item in stored] == list(range(1, 11))
    stream = StreamSimulationProgress(progress=progress, idle_timeout_s=0.1, heartbeat_s=0)
    frames = [
        item
        async for item in stream.execute(
            StreamSimulationProgressRequest(run_id=run_id, last_event_id=stored[4].event_id)
        )
    ]
    replay = [
        item
        for item in frames
        if isinstance(item, ProgressEventView) and item.kind is not ProgressKind.STREAM_CLOSED
    ]
    assert [item.sequence for item in replay] == [6, 7, 8, 9, 10]


async def test_public_api_runs_on_postgres_through_worker(
    migrated: None,
) -> None:
    settings = Settings(
        _env_file=None,
        database_url=DATABASE_URL or "",
        persistence=Persistence.POSTGRES,
        auth_mode=AuthMode.DEMO,
    )
    app = create_app(settings)
    await seed_demo(app)
    transport = httpx.ASGITransport(app=app, raise_app_exceptions=False)
    async with (
        app.router.lifespan_context(app),
        httpx.AsyncClient(transport=transport, base_url="http://testserver") as client,
    ):
        opened = await client.post(
            "/api/v1/runs",
            json={
                "question": "Persisted simulation",
                "round_cap": 1,
                "stakeholder_ids": ["stk_aerztekammer"],
            },
        )
        assert opened.status_code == 202, opened.text
        run_id = str(opened.json()["run_id"])
        started = await client.post(f"/api/v1/runs/{run_id}:start", json={})
        assert started.status_code == 202, started.text
        job_id = started.json()["job_id"]

        for _ in range(150):
            fetched = await client.get(f"/api/v1/jobs/{job_id}")
            assert fetched.status_code == 200, fetched.text
            if fetched.json()["status"] == "completed":
                break
            await asyncio.sleep(0.02)

        assert fetched.json()["status"] == "completed"
        stream = await client.get(f"/api/v1/runs/{run_id}/stream")
        assert stream.status_code == 200, stream.text
        assert "event: run.completed" in stream.text
