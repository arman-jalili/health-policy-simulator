"""Behaviour of the evidence requirement (issue #290)."""

from __future__ import annotations

import pytest

from negotiation_session.domain.entities import NegotiationMandate
from negotiation_session.domain.errors import ArgumentWithoutEvidence
from negotiation_session.domain.events import ArgumentSubmitted
from negotiation_session.domain.simulation_run import SimulationRun
from negotiation_session.domain.values import (
    ArgumentStance,
    ClaimEvidence,
    ClaimStatement,
    EvidencePackId,
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


def _evidence() -> ClaimEvidence:
    return ClaimEvidence(EvidencePackId("pack_1"), "psg_1", "support")


def test_an_argument_without_evidence_is_refused_and_not_recorded() -> None:
    run = _run()
    with pytest.raises(ArgumentWithoutEvidence):
        run.take_turn(
            STAKEHOLDER_A,
            TargetRef(topic=TOPIC),
            ArgumentStance.SUPPORT,
            "Trust me.",
            (),
            (),
        )
    assert run.current_round.arguments == []


def test_an_unsupported_flagged_argument_is_accepted() -> None:
    run = _run()
    argument = run.take_turn(
        STAKEHOLDER_A,
        TargetRef(topic=TOPIC),
        ArgumentStance.SUPPORT,
        "No data yet, flagging it.",
        (ClaimStatement(text="Costs will rise", verdict="unsupported"),),
        (),
        unsupported=True,
    )
    assert argument.is_evidenced
    assert argument.unsupported
    assert run.current_round.arguments == [argument]
    assert any(isinstance(event, ArgumentSubmitted) for event in run.events)


def test_an_evidenced_argument_is_accepted() -> None:
    run = _run()
    argument = run.take_turn(
        STAKEHOLDER_A,
        TargetRef(topic=TOPIC),
        ArgumentStance.SUPPORT,
        "See the pack.",
        (),
        [_evidence()],
    )
    assert argument.evidence[0].evidence_id == EvidencePackId("pack_1")
    assert not argument.unsupported


def test_an_initial_position_without_evidence_is_refused() -> None:
    run = _run()
    with pytest.raises(ArgumentWithoutEvidence):
        run.submit_initial_position(
            STAKEHOLDER_A, TOPIC, ArgumentStance.SUPPORT, Proposal(summary="A"), ()
        )
