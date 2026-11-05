"""Contract freeze: crash recovery (issue #205)."""

from __future__ import annotations

from tests.unit.simulation_orchestration_contract_helpers import (
    field_names,
    method_names,
    parameter_names,
)

from simulation_orchestration.application.dto import JobRecord
from simulation_orchestration.application.events import RunFailed
from simulation_orchestration.application.repositories import JobStore
from simulation_orchestration.application.rules import CheckpointPolicy, RetryPolicy


def test_retry_and_checkpoint_policies_are_frozen() -> None:
    assert method_names(RetryPolicy) == {"delay_seconds", "should_retry"}
    assert parameter_names(RetryPolicy.should_retry) == ["self", "attempts", "error"]
    assert method_names(CheckpointPolicy) == {"checkpoint", "is_safe_boundary"}


def test_job_record_carries_attempts_and_checkpoint() -> None:
    assert {"attempts", "checkpoint", "status", "error"} <= set(field_names(JobRecord))
    assert "list_resumable" in method_names(JobStore)


def test_failure_event_is_frozen() -> None:
    assert RunFailed.name == "RunFailed"
    assert field_names(RunFailed) == ["run_id", "error", "attempts"]


# --- behaviour: checkpointing and bounded retry (issue #212) --------------------------------

from datetime import UTC, datetime  # noqa: E402
from decimal import Decimal  # noqa: E402

import pytest  # noqa: E402

from simulation_orchestration.application.state import initial_state  # noqa: E402
from simulation_orchestration.application.values import (  # noqa: E402
    BudgetUsage,
    GraphState,
    JobId,
    JobStatus,
    RunId,
    RunPhase,
)
from simulation_orchestration.infrastructure.memory import InMemoryJobStore  # noqa: E402


def _state(phase: RunPhase = RunPhase.ROUNDS, round_no: int = 3) -> GraphState:
    base = initial_state(RunId("run_1"))
    return GraphState(
        run_id=base.run_id,
        round=round_no,
        phase=phase,
        next_actor="oegk",
        budget_used=BudgetUsage(invocations=4, tokens=800, cost=Decimal("0.08")),
    )


def test_retry_is_bounded_and_error_sensitive() -> None:
    policy = RetryPolicy(max_attempts=3, base_delay_s=1.0, max_delay_s=5.0)

    assert policy.should_retry(attempts=0, error="boom") is True
    assert policy.should_retry(attempts=2, error="boom") is True
    assert policy.should_retry(attempts=3, error="boom") is False
    assert policy.should_retry(attempts=1, error="   ") is False
    assert [policy.delay_seconds(n) for n in (1, 2, 3, 4)] == [1.0, 2.0, 4.0, 5.0]


def test_retry_policy_rejects_invalid_configuration_and_attempts() -> None:
    with pytest.raises(ValueError, match="max_attempts"):
        RetryPolicy(max_attempts=0)
    with pytest.raises(ValueError, match="positive"):
        RetryPolicy(base_delay_s=0)
    with pytest.raises(ValueError, match="attempts"):
        RetryPolicy().delay_seconds(0)


def test_checkpoint_is_identical_and_terminal_state_is_refused() -> None:
    policy = CheckpointPolicy()
    state = _state()

    assert policy.is_safe_boundary(state) is True
    assert policy.checkpoint(state) == state
    assert policy.is_safe_boundary(_state(RunPhase.DONE)) is False
    with pytest.raises(ValueError, match="terminal"):
        policy.checkpoint(_state(RunPhase.DONE))


async def test_crash_restart_keeps_the_last_round_and_lists_running_job() -> None:
    now = datetime(2026, 11, 6, tzinfo=UTC)
    job = JobRecord(
        job_id=JobId("job_1"),
        run_id=RunId("run_1"),
        status=JobStatus.RUNNING,
        attempts=1,
        checkpoint=_state(),
        budget_used=BudgetUsage(),
        error=None,
        claimed_by="dead-worker",
        created_at=now,
        updated_at=now,
    )
    jobs = InMemoryJobStore()
    await jobs.add(job)

    resumable = await jobs.list_resumable()

    assert [item.checkpoint.round for item in resumable] == [3]
    assert [item.checkpoint for item in resumable] == [_state()]
