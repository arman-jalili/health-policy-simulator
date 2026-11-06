"""Contract freeze: round close guard (issue #282, implements #287)."""

from __future__ import annotations

from tests.unit.negotiation_session_contract_helpers import (
    method_names,
    parameter_names,
)

from negotiation_session.application.services import RecordAbstention
from negotiation_session.domain.entities import NegotiationRound
from negotiation_session.domain.errors import (
    RoundCloseGuardViolation,
    RoundLearningMissing,
    RoundStillOpen,
)
from negotiation_session.domain.simulation_run import SimulationRun
from negotiation_session.domain.values import TurnOutcome


def test_round_close_requires_every_bound_stakeholder_to_be_accounted_for() -> None:
    assert "assert_everyone_accounted_for" in method_names(NegotiationRound)
    assert parameter_names(NegotiationRound.assert_everyone_accounted_for) == ["self", "bound"]
    assert parameter_names(SimulationRun.close_round) == ["self", "learning"]


def test_abstention_is_a_first_class_recorded_outcome() -> None:
    assert {"record_abstention", "record_position", "record_argument"} <= method_names(
        NegotiationRound
    )
    assert parameter_names(NegotiationRound.record_abstention) == [
        "self",
        "stakeholder",
        "topic",
    ]
    assert {member.value for member in TurnOutcome} == {"pending", "spoke", "abstained"}
    assert parameter_names(RecordAbstention.execute) == ["self", "request"]


def test_round_guard_violations_have_stable_codes() -> None:
    assert RoundCloseGuardViolation.code == "ROUND_CLOSE_GUARD_VIOLATION"
    assert RoundStillOpen.code == "ROUND_STILL_OPEN"
    assert RoundLearningMissing.code == "ROUND_LEARNING_MISSING"
