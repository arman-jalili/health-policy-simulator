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
        "budget_exhausted",
    }


def test_resume_reads_the_persisted_checkpoint() -> None:
    assert "checkpoint" in field_names(JobSnapshotResult)
    assert "checkpoint" in field_names(PauseResumeResult)
    assert field_names(GraphState)[:3] == ["run_id", "round", "phase"]


def test_job_store_exposes_both_run_lookup_and_save() -> None:
    assert {"get_by_run", "save", "list_resumable"} <= method_names(JobStore)
