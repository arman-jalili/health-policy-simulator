"""Contract freeze: pause boundary (issue #205)."""

from __future__ import annotations

from tests.unit.simulation_orchestration_contract_helpers import (
    enum_values,
    field_names,
    method_names,
    parameter_names,
)

from simulation_orchestration.application.events import RunPaused
from simulation_orchestration.application.rules import PauseBoundary
from simulation_orchestration.application.services import PauseOrResumeSimulation
from simulation_orchestration.application.values import PauseAction, PauseDecision


def test_pause_actions_are_frozen() -> None:
    assert enum_values(PauseAction) == {"pause", "resume"}


def test_pause_is_decided_at_a_boundary() -> None:
    assert method_names(PauseBoundary) == {"can_pause", "resolve"}
    assert parameter_names(PauseBoundary.resolve) == [
        "self",
        "action",
        "state",
        "turn_committed",
    ]
    assert field_names(PauseDecision) == ["accepted", "checkpoint", "reason"]


def test_pause_service_and_event_are_frozen() -> None:
    assert parameter_names(PauseOrResumeSimulation.execute) == ["self", "request"]
    assert RunPaused.name == "RunPaused"
    assert field_names(RunPaused) == ["run_id", "reason", "checkpoint"]


# --- behaviour: pause/resume at a turn boundary (issue #210) --------------------------------

from datetime import UTC, datetime  # noqa: E402
from typing import Any, cast  # noqa: E402

import pytest  # noqa: E402

from simulation_orchestration.application.commands import (  # noqa: E402
    PauseOrResumeSimulationRequest,
)
from simulation_orchestration.application.dto import JobRecord  # noqa: E402
from simulation_orchestration.application.errors import (  # noqa: E402
    InvalidJobTransition,
    SimulationRunNotFound,
)
from simulation_orchestration.application.state import initial_state  # noqa: E402
from simulation_orchestration.application.values import (  # noqa: E402
    BudgetUsage,
    GraphState,
    JobId,
    JobStatus,
    RunId,
    RunPhase,
)
from simulation_orchestration.infrastructure.memory import (  # noqa: E402
    InMemoryJobStore,
    InMemoryProgressStore,
)


class _Clock:
    def now(self) -> datetime:
        return datetime(2026, 11, 6, tzinfo=UTC)


def _state(phase: RunPhase = RunPhase.ROUNDS) -> GraphState:
    state = initial_state(RunId("run_1"))
    return GraphState(
        run_id=state.run_id,
        round=2,
        phase=phase,
        next_actor="oegk",
        budget_used=BudgetUsage(),
    )


def _job(status: JobStatus = JobStatus.RUNNING) -> JobRecord:
    now = _Clock().now()
    return JobRecord(
        job_id=JobId("job_1"),
        run_id=RunId("run_1"),
        status=status,
        attempts=1,
        checkpoint=_state(),
        budget_used=BudgetUsage(),
        error=None,
        claimed_by="worker-1",
        created_at=now,
        updated_at=now,
    )


async def _service(
    job: JobRecord | None = None,
) -> tuple[PauseOrResumeSimulation, InMemoryJobStore, InMemoryProgressStore]:
    jobs = InMemoryJobStore()
    if job is not None:
        await jobs.add(job)
    progress = InMemoryProgressStore()
    return (
        PauseOrResumeSimulation(
            jobs=jobs, progress=progress, clock=_Clock(), uow=cast(Any, _NoopUow())
        ),
        jobs,
        progress,
    )


class _NoopUow:
    def transaction(self) -> object:
        raise AssertionError("pause service does not open a transaction directly")


def test_pause_is_rejected_at_the_terminal_phase() -> None:
    boundary = PauseBoundary()

    assert boundary.can_pause(_state()) is True
    assert boundary.can_pause(_state(RunPhase.DONE)) is False
    assert (
        boundary.resolve(
            action=PauseAction.PAUSE, state=_state(RunPhase.DONE), turn_committed=True
        ).accepted
        is False
    )


def test_uncommitted_turn_is_discarded_before_checkpoint() -> None:
    decision = PauseBoundary().resolve(
        action=PauseAction.PAUSE, state=_state(), turn_committed=False
    )

    assert decision.accepted is True
    assert "discarded" in (decision.reason or "")


async def test_pause_changes_status_only_and_emits_an_ordered_event() -> None:
    service, jobs, progress = await _service(_job(JobStatus.QUEUED))
    before = await jobs.get_by_run(RunId("run_1"))

    result = await service.execute(
        PauseOrResumeSimulationRequest(
            run_id=RunId("run_1"), action=PauseAction.PAUSE, reason="operator"
        )
    )

    after = await jobs.get_by_run(RunId("run_1"))
    events = await progress.list_after(RunId("run_1"), 0, 10)
    assert result.status is JobStatus.PAUSED
    assert before is not None
    assert after is not None
    assert after.checkpoint == before.checkpoint
    assert after.status is JobStatus.PAUSED
    assert events[0].sequence == 1
    assert events[0].payload["reason"] == "operator"


async def test_resume_requeues_from_the_same_checkpoint() -> None:
    service, jobs, progress = await _service(_job(JobStatus.PAUSED))
    checkpoint = (await jobs.get_by_run(RunId("run_1"))).checkpoint  # type: ignore[union-attr]

    result = await service.execute(
        PauseOrResumeSimulationRequest(run_id=RunId("run_1"), action=PauseAction.RESUME)
    )

    job = await jobs.get_by_run(RunId("run_1"))
    events = await progress.list_after(RunId("run_1"), 0, 10)
    assert result.status is JobStatus.QUEUED
    assert job is not None
    assert job.status is JobStatus.QUEUED
    assert job.checkpoint == checkpoint
    assert events[0].payload["checkpoint"]["round"] == checkpoint.round


async def test_resume_of_a_running_job_is_rejected() -> None:
    service, _, _ = await _service(_job())

    with pytest.raises(InvalidJobTransition, match="cannot resume"):
        await service.execute(
            PauseOrResumeSimulationRequest(run_id=RunId("run_1"), action=PauseAction.RESUME)
        )


async def test_missing_run_is_reported() -> None:
    service, _, _ = await _service()

    with pytest.raises(SimulationRunNotFound):
        await service.execute(
            PauseOrResumeSimulationRequest(run_id=RunId("missing"), action=PauseAction.PAUSE)
        )
