"""Contract freeze: aggregate root ``SimulationRun`` (issue #282, implements #283)."""

from __future__ import annotations

import pytest
from tests.unit.negotiation_session_contract_helpers import field_names, parameter_names

from negotiation_session.domain.entities import NegotiationMandate
from negotiation_session.domain.simulation_run import SimulationRun
from negotiation_session.domain.values import MandateId, RunId, StoppingConditionName


def test_aggregate_fields_are_frozen() -> None:
    assert field_names(SimulationRun) == [
        "id",
        "mandate",
        "phase",
        "round_cap",
        "bound",
        "rounds",
        "conflicts",
        "coalitions",
        "events",
    ]


def test_aggregate_exposes_the_frozen_command_surface() -> None:
    for name in (
        "open",
        "open_round",
        "submit_initial_position",
        "take_turn",
        "revise_position",
        "record_abstention",
        "track_conflict",
        "form_coalition",
        "close_round",
        "evaluate_stopping",
        "advance_phase",
        "turn_order",
        "drain_events",
        "open_position",
        "position_by_id",
    ):
        assert callable(getattr(SimulationRun, name)), name
    assert isinstance(vars(SimulationRun)["is_closed"], property)
    assert isinstance(vars(SimulationRun)["current_round"], property)


def test_factory_and_turn_signatures_are_frozen() -> None:
    assert parameter_names(SimulationRun.open) == ["run_id", "mandate", "bound"]
    assert parameter_names(SimulationRun.open_round) == ["self"]
    assert parameter_names(SimulationRun.take_turn) == [
        "self",
        "stakeholder",
        "target",
        "stance",
        "text",
        "claims",
        "evidence",
        "unsupported",
        "invocation_id",
    ]


def test_stubs_name_the_implementing_issue() -> None:
    mandate = NegotiationMandate(
        id=MandateId("mnd_1"),
        question="How to stabilise costs?",
        objective="Agreement on measures",
        constraints=(),
        round_cap=5,
        stopping_conditions=(StoppingConditionName.CONSENSUS,),
        profile_version="v1",
    )
    with pytest.raises(NotImplementedError, match="#283"):
        SimulationRun.open(run_id=RunId("run_1"), mandate=mandate, bound={})
