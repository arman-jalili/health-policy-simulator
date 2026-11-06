"""Behaviour of round learning capture and carry-forward (issue #294)."""

from __future__ import annotations

import pytest

from negotiation_session.domain.entities import NegotiationMandate, RoundLearning
from negotiation_session.domain.errors import RoundLearningMissing
from negotiation_session.domain.events import RoundLearningCaptured
from negotiation_session.domain.simulation_run import SimulationRun
from negotiation_session.domain.values import (
    ArgumentId,
    LearningId,
    LearningInsight,
    LearningInsightType,
    MandateId,
    RunId,
    StakeholderBinding,
    StakeholderId,
    StoppingConditionName,
    TopicRef,
)

STAKEHOLDER_A = StakeholderId("stk_a")
TOPIC = TopicRef("costs")


def _run() -> SimulationRun:
    run = SimulationRun.open(
        run_id=RunId("run_1"),
        mandate=NegotiationMandate(
            id=MandateId("mnd_1"),
            question="How to stabilise costs?",
            objective="Agreement",
            constraints=(),
            round_cap=5,
            stopping_conditions=(StoppingConditionName.CONSENSUS,),
            profile_version="v1",
        ),
        bound={STAKEHOLDER_A: StakeholderBinding(STAKEHOLDER_A, "A", "A")},
    )
    run.open_round()
    return run


def _insights() -> tuple[LearningInsight, ...]:
    return (
        LearningInsight(
            insight_type=LearningInsightType.BLOCKING_CONSTRAINT,
            statement="The insurer will not accept a flat cap.",
            derived_from=(ArgumentId("arg_1"),),
            round_number=1,
        ),
        LearningInsight(
            insight_type=LearningInsightType.EVIDENCE_GAP,
            statement="No cost data for the rural population.",
            round_number=1,
        ),
    )


def _learning() -> RoundLearning:
    return RoundLearning.capture(
        learning_id=LearningId("lrn_1"),
        round_number=1,
        insights=_insights(),
    )


def test_capture_keeps_insights_and_prompt_payload() -> None:
    learning = _learning()
    assert learning.round_number == 1
    assert len(learning.insights) == 2
    payload = learning.to_prompt_payload()
    assert payload["round"] == 1
    insights = payload["insights"]
    assert isinstance(insights, list)
    assert insights[0]["type"] == "blocking_constraint"
    assert insights[0]["derived_from"] == ["arg_1"]
    assert insights[1]["type"] == "evidence_gap"


def test_a_round_cannot_close_without_learning() -> None:
    run = _run()
    run.record_abstention(STAKEHOLDER_A, TOPIC)
    with pytest.raises(RoundLearningMissing):
        run.current_round.close()


def test_learning_is_captured_and_carried_into_the_next_round() -> None:
    run = _run()
    run.record_abstention(STAKEHOLDER_A, TOPIC)
    learning = _learning()
    run.close_round(learning)
    captured = [event for event in run.events if isinstance(event, RoundLearningCaptured)]
    assert len(captured) == 1
    assert captured[0].insight_count == 2
    assert captured[0].insight_types == ("blocking_constraint", "evidence_gap")

    second = run.open_round()
    assert second.learning is learning
    payload = second.carry_learning()
    assert payload is not None
    assert payload.to_prompt_payload()["round"] == 1
