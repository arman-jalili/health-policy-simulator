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
