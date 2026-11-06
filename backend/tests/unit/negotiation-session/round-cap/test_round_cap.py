"""Contract freeze: round cap (issue #282, implements #292)."""

from __future__ import annotations

from tests.unit.negotiation_session_contract_helpers import (
    enum_values,
    field_names,
    parameter_names,
)

from negotiation_session.domain.errors import RoundCapExceeded
from negotiation_session.domain.events import SimulationRunClosed
from negotiation_session.domain.services import EvaluateStoppingCondition
from negotiation_session.domain.simulation_run import SimulationRun
from negotiation_session.domain.values import StoppingCondition, StoppingConditionName


def test_stopping_condition_is_a_named_rule_with_parameters() -> None:
    assert field_names(StoppingCondition) == ["name", "fired", "parameters"]
    assert enum_values(StoppingConditionName) == {"consensus", "round_cap", "deadlock"}
    assert parameter_names(StoppingCondition.evaluate) == [
        "consensus",
        "rounds_done",
        "round_cap",
        "deadlocked",
    ]


def test_domain_service_evaluates_the_same_rule() -> None:
    assert parameter_names(EvaluateStoppingCondition.evaluate) == [
        "self",
        "consensus",
        "rounds_done",
        "round_cap",
        "deadlocked",
    ]
    assert parameter_names(SimulationRun.evaluate_stopping) == ["self", "consensus"]


def test_cap_violation_and_terminal_event_are_frozen() -> None:
    assert RoundCapExceeded.code == "ROUND_CAP_EXCEEDED"
    assert field_names(SimulationRunClosed) == [
        "run_id",
        "condition",
        "rounds",
        "final_phase",
    ]
    assert SimulationRunClosed.name == "SimulationRunClosed"
