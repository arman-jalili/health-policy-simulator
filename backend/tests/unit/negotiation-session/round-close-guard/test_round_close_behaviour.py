"""Behaviour of the round close guard (issue #287)."""

from __future__ import annotations

import pytest

from negotiation_session.domain.entities import NegotiationMandate, RoundLearning
from negotiation_session.domain.errors import (
    RoundCloseGuardViolation,
    RoundLearningMissing,
    RoundStillOpen,
)
from negotiation_session.domain.simulation_run import SimulationRun
from negotiation_session.domain.values import (
    ArgumentStance,
    ClaimEvidence,
    EvidencePackId,
    LearningId,
    MandateId,
    Proposal,
    RunId,
    StakeholderBinding,
    StakeholderId,
    StoppingConditionName,
    TargetRef,
    TopicRef,
)

STAKEHOLDER_A = StakeholderId("stk_a")
STAKEHOLDER_B = StakeholderId("stk_b")
TOPIC = TopicRef("costs")


def _run() -> SimulationRun:
    return SimulationRun.open(
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
        bound={
            STAKEHOLDER_A: StakeholderBinding(STAKEHOLDER_A, "A", "A"),
            STAKEHOLDER_B: StakeholderBinding(STAKEHOLDER_B, "B", "B"),
        },
    )


def _evidence() -> ClaimEvidence:
    return ClaimEvidence(EvidencePackId("pack_1"), "psg_1", "support")


def _learning(round_number: int = 1) -> RoundLearning:
    return RoundLearning(LearningId(f"lrn_{round_number}"), round_number)


def test_a_position_alone_does_not_account_for_a_stakeholder() -> None:
    run = _run()
    run.open_round()
    run.submit_initial_position(
        STAKEHOLDER_A, TOPIC, ArgumentStance.SUPPORT, Proposal(summary="A"), [_evidence()]
    )
    run.record_abstention(STAKEHOLDER_B, TOPIC)
    with pytest.raises(RoundCloseGuardViolation):
        run.close_round(_learning())


def test_all_turns_close_the_round() -> None:
    run = _run()
    round_ = run.open_round()
    for stakeholder in (STAKEHOLDER_A, STAKEHOLDER_B):
        run.take_turn(
            stakeholder,
            TargetRef(topic=TOPIC),
            ArgumentStance.SUPPORT,
            "text",
            (),
            [_evidence()],
        )
    run.close_round(_learning())
    assert round_.is_closed
    assert round_.learning is not None


def test_all_abstentions_close_the_round() -> None:
    run = _run()
    round_ = run.open_round()
    run.record_abstention(STAKEHOLDER_A, TOPIC)
    run.record_abstention(STAKEHOLDER_B, TOPIC)
    run.close_round(_learning())
    assert round_.is_closed


def test_a_closed_round_cannot_be_closed_again() -> None:
    run = _run()
    run.open_round()
    run.record_abstention(STAKEHOLDER_A, TOPIC)
    run.record_abstention(STAKEHOLDER_B, TOPIC)
    run.close_round(_learning())
    with pytest.raises(RoundStillOpen):
        run.close_round(_learning())


def test_a_round_cannot_close_without_learning() -> None:
    run = _run()
    round_ = run.open_round()
    with pytest.raises(RoundLearningMissing):
        round_.close()
