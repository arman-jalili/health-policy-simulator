"""Contract freeze: one open position (issue #282, implements #289)."""

from __future__ import annotations

from tests.unit.negotiation_session_contract_helpers import (
    field_names,
    method_names,
    parameter_names,
)

from negotiation_session.application.services import SubmitInitialPosition
from negotiation_session.domain.entities import NegotiationRound, Position
from negotiation_session.domain.simulation_run import SimulationRun


def test_position_keeps_its_lineage_instead_of_duplicating() -> None:
    assert field_names(Position) == [
        "id",
        "stakeholder",
        "topic",
        "stance",
        "proposal",
        "evidence",
        "round_number",
        "revision",
        "supersedes",
        "superseded_by",
    ]
    assert isinstance(vars(Position)["is_open"], property)


def test_supersede_replaces_the_open_position_with_a_new_one() -> None:
    assert "supersede" in method_names(Position)
    assert parameter_names(Position.supersede) == ["self", "new_id", "stance", "reason"]
    assert parameter_names(Position.initial) == [
        "position_id",
        "stakeholder",
        "topic",
        "stance",
        "proposal",
        "evidence",
        "round_number",
    ]


def test_round_and_aggregate_expose_one_open_position_lookup() -> None:
    assert parameter_names(NegotiationRound.open_position_for) == [
        "self",
        "stakeholder",
        "topic",
    ]
    assert parameter_names(SimulationRun.open_position) == ["self", "stakeholder", "topic"]
    assert parameter_names(SubmitInitialPosition.execute) == ["self", "request"]
