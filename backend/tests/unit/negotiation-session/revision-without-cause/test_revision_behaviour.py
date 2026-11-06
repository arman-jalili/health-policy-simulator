"""Behaviour of revision-without-cause rejection (issue #288)."""

from __future__ import annotations

import pytest

from negotiation_session.domain.entities import NegotiationMandate, RoundLearning
from negotiation_session.domain.errors import PositionNotFound, RevisionWithoutCause
from negotiation_session.domain.events import PositionRevised, PositionRevisionRejected
from negotiation_session.domain.simulation_run import SimulationRun
from negotiation_session.domain.values import (
    ArgumentId,
    ArgumentStance,
    ClaimEvidence,
    EvidencePackId,
    LearningId,
    MandateId,
    Proposal,
    RevisionReason,
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
        bound={
            STAKEHOLDER_A: StakeholderBinding(STAKEHOLDER_A, "A", "A"),
            STAKEHOLDER_B: StakeholderBinding(STAKEHOLDER_B, "B", "B"),
        },
    )
    run.open_round()
    run.submit_initial_position(
        STAKEHOLDER_A, TOPIC, ArgumentStance.SUPPORT, Proposal(summary="A"), [_evidence("pack_1")]
    )
    return run


def _evidence(pack: str) -> ClaimEvidence:
    return ClaimEvidence(EvidencePackId(pack), "psg_1", "support")


def test_an_empty_reason_is_rejected_and_audited() -> None:
    run = _run()
    before = run.open_position(STAKEHOLDER_A, TOPIC)
    seen = len(run.events)
    with pytest.raises(RevisionWithoutCause):
        run.revise_position(STAKEHOLDER_A, TOPIC, ArgumentStance.OPPOSE, RevisionReason())
    after = run.open_position(STAKEHOLDER_A, TOPIC)
    assert after is before
    assert after.stance is ArgumentStance.SUPPORT
    rejected = [event for event in run.events[seen:] if isinstance(event, PositionRevisionRejected)]
    assert len(rejected) == 1
    assert rejected[0].topic == TOPIC


def test_a_reason_citing_an_unknown_argument_is_rejected() -> None:
    run = _run()
    with pytest.raises(RevisionWithoutCause):
        run.revise_position(
            STAKEHOLDER_A,
            TOPIC,
            ArgumentStance.OPPOSE,
            RevisionReason(argument_ids=(ArgumentId("arg_not_in_run"),), driver="invented"),
        )


def test_a_reason_citing_an_evidence_pack_is_accepted() -> None:
    run = _run()
    argument = run.take_turn(
        STAKEHOLDER_A,
        TargetRef(topic=TOPIC),
        ArgumentStance.QUALIFY,
        "New data.",
        (),
        [_evidence("pack_2")],
    )
    revised = run.revise_position(
        STAKEHOLDER_A,
        TOPIC,
        ArgumentStance.OPPOSE,
        RevisionReason(pack_ids=(argument.evidence[0].evidence_id,), driver="new data"),
    )
    assert revised.stance is ArgumentStance.OPPOSE
    assert any(isinstance(event, PositionRevised) for event in run.events)


def test_revision_of_an_unknown_position_raises_not_found() -> None:
    run = _run()
    with pytest.raises(PositionNotFound):
        run.revise_position(
            STAKEHOLDER_A,
            TopicRef("unknown"),
            ArgumentStance.OPPOSE,
            RevisionReason(driver="x"),
        )


def test_revision_works_across_rounds() -> None:
    run = _run()
    run.take_turn(
        STAKEHOLDER_A,
        TargetRef(topic=TOPIC),
        ArgumentStance.SUPPORT,
        "Round one.",
        (),
        [_evidence("pack_5")],
    )
    run.take_turn(
        STAKEHOLDER_B,
        TargetRef(topic=TOPIC),
        ArgumentStance.SUPPORT,
        "Agreed.",
        (),
        [_evidence("pack_3")],
    )
    run.close_round(RoundLearning(LearningId("lrn_1"), 1))
    run.open_round()
    argument = run.take_turn(
        STAKEHOLDER_A,
        TargetRef(topic=TOPIC),
        ArgumentStance.QUALIFY,
        "Second round evidence.",
        (),
        [_evidence("pack_4")],
    )
    revised = run.revise_position(
        STAKEHOLDER_A,
        TOPIC,
        ArgumentStance.OPPOSE,
        RevisionReason(argument_ids=(argument.id,), driver="second round"),
    )
    assert revised.stance is ArgumentStance.OPPOSE
