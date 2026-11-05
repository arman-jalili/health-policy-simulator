"""Worker lifecycle: per-job failure isolation, bounded retries, leases, boot recovery (#235)."""

from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime, timedelta
from typing import Any, cast

from shared.ids import new_id
from shared.metrics import METRICS
from simulation_orchestration.application.commands import StartSimulationRequest
from simulation_orchestration.application.dto import JobRecord
from simulation_orchestration.application.events import RunFailed
from simulation_orchestration.application.ports import NegotiationGateway
from simulation_orchestration.application.repositories import (
    InvocationStore,
    JobStore,
    ProgressStore,
)
from simulation_orchestration.application.rules import (
    BudgetGuard,
    CheckpointPolicy,
    RetryPolicy,
)
from simulation_orchestration.application.services import RunSimulationJob
from simulation_orchestration.application.state import initial_state
from simulation_orchestration.application.values import (
    BudgetUsage,
    GraphState,
    JobId,
    JobStatus,
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


class _Graph:
    def __init__(self, *, fail_on: str | None = None) -> None:
        self._fail_on = fail_on

    def next_node(self, state: GraphState) -> str | None:
        return None if state.phase is RunPhase.DONE else "turn"

    async def step(self, node_name: str, state: GraphState) -> GraphState:
        if self._fail_on is not None and str(state.run_id) == self._fail_on:
            raise RuntimeError("provider exploded")
        return replace(state, phase=RunPhase.DONE, round=state.round + 1)


def _service(
    graph: _Graph,
    *,
    jobs: JobStore | None = None,
    progress: ProgressStore | None = None,
    invocations: InvocationStore | None = None,
) -> tuple[RunSimulationJob, JobStore, ProgressStore]:
    job_store = jobs or InMemoryJobStore()
    progress_store = progress or InMemoryProgressStore()
    service = RunSimulationJob(
        graph=graph,
        negotiation=cast(NegotiationGateway, NoopNegotiationGateway()),
        jobs=job_store,
        invocations=invocations or InMemoryInvocationStore(),
        progress=progress_store,
        budget_guard=BudgetGuard(),
        checkpoint_policy=CheckpointPolicy(),
        clock=_Clock(),
        uow=cast(Any, object()),
    )
    return service, job_store, progress_store


async def _queued(service: RunSimulationJob, run_id: str) -> JobRecord:
    result = await service.execute(StartSimulationRequest(run_id=RunId(run_id)))
    job = await service._jobs.get(result.job_id)
    assert job is not None
    return job


async def test_a_failed_job_does_not_kill_the_worker_and_the_next_job_runs() -> None:
    service, jobs, progress = _service(_Graph(fail_on="run_bad"))
    bad = await _queued(service, "run_bad")
    good = await _queued(service, "run_good")
    worker = BackgroundWorker(service, retry_policy=RetryPolicy(max_attempts=1, base_delay_s=0.001))

    assert await worker.run_once() is True
    assert await worker.run_once() is True
    assert await worker.run_once() is False

    failed = await jobs.get(bad.job_id)
    succeeded = await jobs.get(good.job_id)
    assert failed is not None
    assert failed.status is JobStatus.DEAD_LETTER
    assert "provider exploded" in (failed.error or "")
    assert succeeded is not None
    assert succeeded.status is JobStatus.COMPLETED

    events = await progress.list_after(RunId("run_bad"), 0, 20)
    assert any(event.kind.value == "run.failed" for event in events)
    failed_event = next(event for event in events if event.kind.value == "run.failed")
    assert failed_event.payload["error"].startswith("RuntimeError")
    assert METRICS.value("simulation_job_failures_total") >= 1


async def test_retries_are_bounded_before_dead_letter() -> None:
    service, jobs, _ = _service(_Graph(fail_on="run_retry"))
    job = await _queued(service, "run_retry")
    worker = BackgroundWorker(service, retry_policy=RetryPolicy(max_attempts=2, base_delay_s=0.001))

    assert await worker.run_once() is True
    retryable = await jobs.get(job.job_id)
    assert retryable is not None
    assert retryable.status is JobStatus.QUEUED
    assert retryable.attempts == 1

    assert await worker.run_once() is True
    terminal = await jobs.get(job.job_id)
    assert terminal is not None
    assert terminal.status is JobStatus.DEAD_LETTER
    assert terminal.attempts == 2


async def test_expired_lease_is_reclaimed_but_a_live_lease_is_not() -> None:
    jobs = InMemoryJobStore(lease_seconds=30)
    run_id = RunId("run_lease")
    now = _Clock().now()
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
    await jobs.add(job)

    first = await jobs.claim_next("worker-1", now)
    assert first is not None
    assert await jobs.claim_next("worker-2", now) is None

    expired = replace(first, lease_expires_at=now - timedelta(seconds=1))
    await jobs.save(expired)
    reclaimed = await jobs.claim_next("worker-2", now)

    assert reclaimed is not None
    assert reclaimed.claimed_by == "worker-2"
    assert reclaimed.attempts == 2


async def test_boot_recovery_requeues_a_running_job() -> None:
    service, jobs, _ = _service(_Graph())
    job = await _queued(service, "run_crash")
    claimed = await jobs.claim_next("dead-worker", _Clock().now())
    assert claimed is not None
    worker = BackgroundWorker(service)

    resumable = await worker.recover()

    recovered = await jobs.get(job.job_id)
    assert resumable == 1
    assert recovered is not None
    assert recovered.status is JobStatus.QUEUED
    assert recovered.claimed_by is None
    assert recovered.lease_expires_at is None
    assert recovered.error == "recovered after worker restart"


def test_failure_event_carries_the_run_and_attempts() -> None:
    event = RunFailed(run_id=RunId("run_1"), error="boom", attempts=3)

    assert event.name == "RunFailed"
    assert event.attempts == 3
