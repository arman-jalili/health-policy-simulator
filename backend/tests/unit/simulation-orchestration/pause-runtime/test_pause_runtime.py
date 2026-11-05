"""Runtime proof: pause interrupts before the next node and resume re-enters the worker (#236)."""

from __future__ import annotations

import asyncio
from dataclasses import replace
from datetime import UTC, datetime
from typing import Any, cast

from simulation_orchestration.application.commands import (
    PauseOrResumeSimulationRequest,
    StartSimulationRequest,
)
from simulation_orchestration.application.ports import NegotiationGateway
from simulation_orchestration.application.rules import BudgetGuard, CheckpointPolicy
from simulation_orchestration.application.services import (
    PauseOrResumeSimulation,
    RunSimulationJob,
)
from simulation_orchestration.application.values import (
    GraphState,
    JobStatus,
    PauseAction,
    RunId,
    RunPhase,
)
from simulation_orchestration.infrastructure.memory import (
    InMemoryInvocationStore,
    InMemoryJobStore,
    InMemoryProgressStore,
)
from simulation_orchestration.infrastructure.negotiation import NoopNegotiationGateway
from simulation_orchestration.infrastructure.worker import BackgroundWorker


class _Clock:
    def now(self) -> datetime:
        return datetime(2026, 11, 6, 12, 0, tzinfo=UTC)


class _PauseGraph:
    def __init__(self) -> None:
        self.executed: list[str] = []
        self.started = asyncio.Event()
        self.release = asyncio.Event()

    def next_node(self, state: GraphState) -> str | None:
        if state.phase is RunPhase.MANDATE:
            return "first"
        if state.phase is RunPhase.ROUNDS:
            return "second"
        return None

    async def step(self, node_name: str, state: GraphState) -> GraphState:
        self.executed.append(node_name)
        if node_name == "first":
            self.started.set()
            await self.release.wait()
            return replace(state, phase=RunPhase.ROUNDS, round=state.round + 1)
        return replace(state, phase=RunPhase.DONE, round=state.round + 1)


async def test_pause_commits_the_in_flight_turn_then_resume_runs_the_next_node_once() -> None:
    graph = _PauseGraph()
    jobs = InMemoryJobStore()
    progress = InMemoryProgressStore()
    service = RunSimulationJob(
        graph=graph,
        negotiation=cast(NegotiationGateway, NoopNegotiationGateway()),
        jobs=jobs,
        invocations=InMemoryInvocationStore(),
        progress=progress,
        budget_guard=BudgetGuard(),
        checkpoint_policy=CheckpointPolicy(),
        clock=_Clock(),
        uow=cast(Any, object()),
    )
    pause_service = PauseOrResumeSimulation(
        jobs=jobs, progress=progress, clock=_Clock(), uow=cast(Any, object())
    )
    worker = BackgroundWorker(service)
    started = await service.execute(StartSimulationRequest(run_id=RunId("run_pause")))
    claimed = await jobs.claim_next("worker-1", _Clock().now())
    assert claimed is not None

    run_task = asyncio.create_task(service.run(str(started.job_id)))
    await graph.started.wait()
    pause = await pause_service.execute(
        PauseOrResumeSimulationRequest(
            run_id=RunId("run_pause"), action=PauseAction.PAUSE, reason="operator"
        )
    )
    assert pause.status is JobStatus.PAUSED
    graph.release.set()
    result = await run_task

    paused = await jobs.get(started.job_id)
    assert result.status is JobStatus.PAUSED
    assert paused is not None
    assert paused.status is JobStatus.PAUSED
    assert paused.checkpoint.phase is RunPhase.ROUNDS
    assert graph.executed == ["first"]

    events = await progress.list_after(RunId("run_pause"), 0, 20)
    paused_events = [event for event in events if event.kind.value == "run.paused"]
    assert len(paused_events) == 1
    assert paused_events[0].payload["reason"] == "operator"
    assert paused_events[0].payload["checkpoint"]["phase"] == "rounds"

    resumed = await pause_service.execute(
        PauseOrResumeSimulationRequest(run_id=RunId("run_pause"), action=PauseAction.RESUME)
    )
    assert resumed.status is JobStatus.QUEUED

    assert await worker.run_once() is True
    completed = await jobs.get(started.job_id)
    assert completed is not None
    assert completed.status is JobStatus.COMPLETED
    assert graph.executed == ["first", "second"]
