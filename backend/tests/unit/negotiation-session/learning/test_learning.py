"""Contract freeze: learning (issue #282, implements #294)."""

from __future__ import annotations

from tests.unit.negotiation_session_contract_helpers import (
    field_names,
    method_names,
    parameter_names,
)

from negotiation_session.application.services import CloseRound
from negotiation_session.domain.entities import NegotiationRound, RoundLearning
from negotiation_session.domain.errors import RoundLearningMissing
from negotiation_session.domain.events import LearningApplied, RoundLearningCaptured
from negotiation_session.domain.values import LearningApplication, LearningInsight


def test_round_learning_is_the_close_precondition() -> None:
    assert field_names(RoundLearning) == ["id", "round_number", "insights"]
    assert parameter_names(RoundLearning.capture) == [
        "learning_id",
        "round_number",
        "insights",
    ]
    assert parameter_names(RoundLearning.to_prompt_payload) == ["self"]
    assert RoundLearningMissing.code == "ROUND_LEARNING_MISSING"


def test_learning_is_carried_into_the_next_round() -> None:
    assert {"attach_learning", "carry_learning"} <= method_names(NegotiationRound)
    assert parameter_names(NegotiationRound.carry_learning) == ["self"]
    assert parameter_names(CloseRound.execute) == ["self", "request"]


def test_insights_and_their_application_are_traceable() -> None:
    assert field_names(LearningInsight) == [
        "insight_type",
        "statement",
        "derived_from",
        "round_number",
    ]
    assert field_names(LearningApplication) == [
        "learning_id",
        "learning_round",
        "insight_type",
        "argument_id",
    ]
    assert field_names(RoundLearningCaptured) == [
        "run_id",
        "round",
        "insight_count",
        "insight_types",
    ]
    assert field_names(LearningApplied) == [
        "run_id",
        "stakeholder_id",
        "insight_type",
        "learning_round",
        "argument_id",
    ]
