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
