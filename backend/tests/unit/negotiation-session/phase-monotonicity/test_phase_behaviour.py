"""Behaviour of phase monotonicity (issue #286)."""

from __future__ import annotations

import pytest

from negotiation_session.domain.entities import NegotiationMandate, RoundLearning
from negotiation_session.domain.errors import ClosedRunImmutable, PhaseRegression
from negotiation_session.domain.simulation_run import SimulationRun
from negotiation_session.domain.values import (
    ArgumentStance,
    ClaimEvidence,
    EvidencePackId,
    LearningId,
    MandateId,
    NegotiationPhase,
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


def _learning(round_number: int) -> RoundLearning:
    return RoundLearning(LearningId(f"lrn_{round_number}"), round_number)


def _close_round(run: SimulationRun, round_number: int) -> None:
    run.record_abstention(STAKEHOLDER_A, TOPIC)
    run.record_abstention(STAKEHOLDER_B, TOPIC)
    run.close_round(_learning(round_number))


def test_phase_ranks_are_strictly_monotonic() -> None:
    phases = list(NegotiationPhase)
    assert [phase.rank for phase in phases] == list(range(len(phases)))
    assert NegotiationPhase.DRAFT.can_advance_to(NegotiationPhase.POSITION_FORMATION)
    assert not NegotiationPhase.DEBATE.can_advance_to(NegotiationPhase.POSITION_FORMATION)
    assert NegotiationPhase.CLOSED.is_terminal
    assert not NegotiationPhase.DEBATE.is_terminal


def test_phase_regression_is_refused() -> None:
    run = _run()
    run.advance_phase(NegotiationPhase.DEBATE)
    with pytest.raises(PhaseRegression):
        run.advance_phase(NegotiationPhase.POSITION_FORMATION)
    assert run.phase is NegotiationPhase.DEBATE


def test_second_round_advances_the_phase_and_keeps_the_run_open() -> None:
    run = _run()
    run.open_round()
    _close_round(run, 1)
    run.open_round()
    assert run.phase is NegotiationPhase.DEBATE
    assert len(run.rounds) == 2


def test_closed_run_refuses_every_mutating_command() -> None:
    run = _run()
    run.open_round()
    position = run.submit_initial_position(
        STAKEHOLDER_A, TOPIC, ArgumentStance.SUPPORT, Proposal(summary="A"), [_evidence()]
    )
    run.advance_phase(NegotiationPhase.CLOSED)
    commands = [
        lambda: run.open_round(),
        lambda: run.submit_initial_position(
            STAKEHOLDER_A, TOPIC, ArgumentStance.OPPOSE, Proposal(summary="B"), [_evidence()]
        ),
        lambda: run.take_turn(
            STAKEHOLDER_A,
            TargetRef(topic=TOPIC),
            ArgumentStance.SUPPORT,
            "text",
            (),
            [_evidence()],
        ),
        lambda: run.revise_position(
            STAKEHOLDER_A, TOPIC, ArgumentStance.OPPOSE, RevisionReason(driver="x")
        ),
        lambda: run.record_abstention(STAKEHOLDER_B, TOPIC),
        lambda: run.track_conflict(TOPIC, {STAKEHOLDER_A: ArgumentStance.SUPPORT}),
        lambda: run.close_round(_learning(1)),
    ]
    for command in commands:
        with pytest.raises(ClosedRunImmutable):
            command()
    assert position.is_open
    assert run.phase is NegotiationPhase.CLOSED
