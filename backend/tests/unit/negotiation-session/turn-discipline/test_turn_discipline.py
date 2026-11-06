"""Contract freeze: turn discipline (issue #282, implements #291)."""

from __future__ import annotations

from tests.unit.negotiation_session_contract_helpers import (
    field_names,
    method_names,
    parameter_names,
)

from negotiation_session.domain.entities import NegotiationRound
from negotiation_session.domain.errors import DuplicateTurn, TurnNotAvailable
from negotiation_session.domain.services import (
    AffectedFirstTurnOrder,
    PowerWeightedTurnOrder,
    RoundRobinTurnOrder,
    TurnOrderPolicy,
)
from negotiation_session.domain.simulation_run import SimulationRun
from negotiation_session.domain.values import TurnAssignment


def test_a_turn_is_addressable_by_stakeholder_topic_and_order() -> None:
    assert field_names(TurnAssignment) == ["stakeholder", "topic", "order", "outcome"]


def test_round_refuses_out_of_turn_and_duplicate_turns() -> None:
    assert parameter_names(NegotiationRound.assert_turn_available) == [
        "self",
        "stakeholder",
        "topic",
    ]
    assert parameter_names(NegotiationRound.record_argument) == ["self", "argument"]
    assert TurnNotAvailable.code == "TURN_NOT_AVAILABLE"
    assert DuplicateTurn.code == "DUPLICATE_TURN"


def test_turn_order_policy_is_a_domain_strategy() -> None:
    for strategy in (RoundRobinTurnOrder, PowerWeightedTurnOrder, AffectedFirstTurnOrder):
        assert "assign" in method_names(strategy), strategy.__name__
    assert "assign" in method_names(TurnOrderPolicy)
    assert parameter_names(TurnOrderPolicy.assign) == [
        "self",
        "bound",
        "round_number",
        "topics",
    ]
    assert parameter_names(SimulationRun.turn_order) == ["self"]
