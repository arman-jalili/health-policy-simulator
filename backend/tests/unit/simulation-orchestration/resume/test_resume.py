"""Contract freeze: resume (issue #205)."""

from __future__ import annotations

from tests.unit.simulation_orchestration_contract_helpers import (
    enum_values,
    field_names,
    method_names,
)

from simulation_orchestration.application.dto import JobSnapshotResult, PauseResumeResult
from simulation_orchestration.application.repositories import JobStore
from simulation_orchestration.application.values import GraphState, JobStatus


def test_job_lifecycle_has_a_paused_state() -> None:
    assert enum_values(JobStatus) == {
        "queued",
        "running",
        "paused",
        "completed",
        "failed",
        "dead_letter",
        "budget_exhausted",
    }


def test_resume_reads_the_persisted_checkpoint() -> None:
    assert "checkpoint" in field_names(JobSnapshotResult)
    assert "checkpoint" in field_names(PauseResumeResult)
    assert field_names(GraphState)[:3] == ["run_id", "round", "phase"]


def test_job_store_exposes_both_run_lookup_and_save() -> None:
    assert {"get_by_run", "save", "list_resumable"} <= method_names(JobStore)


# --- behaviour: resume at the next turn with identical prior state (issue #211) -------------

from datetime import UTC, datetime  # noqa: E402
from decimal import Decimal  # noqa: E402
from typing import Any, cast  # noqa: E402

import pytest  # noqa: E402

from simulation_orchestration.application.commands import (  # noqa: E402
    PauseOrResumeSimulationRequest,
)
from simulation_orchestration.application.dto import JobRecord  # noqa: E402
from simulation_orchestration.application.errors import InvalidJobTransition  # noqa: E402
from simulation_orchestration.application.services import (  # noqa: E402
    PauseOrResumeSimulation,
)
from simulation_orchestration.application.state import initial_state  # noqa: E402
from simulation_orchestration.application.values import (  # noqa: E402
    BudgetUsage,
    JobId,
    PauseAction,
    RunId,
    RunPhase,
)
from simulation_orchestration.infrastructure.memory import (  # noqa: E402
    InMemoryJobStore,
    InMemoryProgressStore,
)


class _Clock:
    def now(self) -> datetime:
        return datetime(2026, 11, 6, 12, 0, tzinfo=UTC)


def _checkpoint() -> GraphState:
    base = initial_state(RunId("run_1"))
    return GraphState(
        run_id=base.run_id,
        round=4,
        phase=RunPhase.ROUNDS,
        next_actor="patientenanwaltschaft",
        budget_used=BudgetUsage(invocations=8, tokens=4096, cost=Decimal("0.42")),
    )


def _job(status: JobStatus) -> JobRecord:
    now = datetime(2026, 11, 6, 11, 0, tzinfo=UTC)
    return JobRecord(
        job_id=JobId("job_1"),
        run_id=RunId("run_1"),
        status=status,
        attempts=2,
        checkpoint=_checkpoint(),
        budget_used=BudgetUsage(invocations=8, tokens=4096, cost=Decimal("0.42")),
        error="old failure",
        claimed_by="worker-1",
        created_at=now,
        updated_at=now,
    )


async def test_resume_preserves_round_phase_budget_and_clears_worker_claim() -> None:
    jobs = InMemoryJobStore()
    await jobs.add(_job(JobStatus.PAUSED))
    service = PauseOrResumeSimulation(
        jobs=jobs,
        progress=InMemoryProgressStore(),
        clock=_Clock(),
        uow=cast(Any, object()),
    )

    await service.execute(
        PauseOrResumeSimulationRequest(run_id=RunId("run_1"), action=PauseAction.RESUME)
    )

    job = await jobs.get_by_run(RunId("run_1"))
    assert job is not None
    assert job.status is JobStatus.QUEUED
    assert job.checkpoint == _checkpoint()
    assert job.budget_used == BudgetUsage(invocations=8, tokens=4096, cost=Decimal("0.42"))
    assert job.claimed_by is None
    assert job.updated_at == _Clock().now()


async def test_completed_job_cannot_resume() -> None:
    jobs = InMemoryJobStore()
    await jobs.add(_job(JobStatus.COMPLETED))
    service = PauseOrResumeSimulation(
        jobs=jobs,
        progress=InMemoryProgressStore(),
        clock=_Clock(),
        uow=cast(Any, object()),
    )

    with pytest.raises(InvalidJobTransition, match="cannot resume"):
        await service.execute(
            PauseOrResumeSimulationRequest(run_id=RunId("run_1"), action=PauseAction.RESUME)
        )


async def test_resumed_job_is_claimable_by_the_worker() -> None:
    jobs = InMemoryJobStore()
    await jobs.add(_job(JobStatus.PAUSED))
    service = PauseOrResumeSimulation(
        jobs=jobs,
        progress=InMemoryProgressStore(),
        clock=_Clock(),
        uow=cast(Any, object()),
    )
    await service.execute(
        PauseOrResumeSimulationRequest(run_id=RunId("run_1"), action=PauseAction.RESUME)
    )

    claimed = await jobs.claim_next("worker-1", datetime(2026, 11, 6, 13, 0, tzinfo=UTC))

    assert claimed is not None
    assert claimed.job_id == "job_1"
    assert claimed.status is JobStatus.RUNNING
