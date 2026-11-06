"""Behaviour of closed-run immutability (issue #295)."""

from __future__ import annotations

import pytest

from negotiation_session.domain.entities import NegotiationMandate, RoundLearning
from negotiation_session.domain.errors import ClosedRunImmutable
from negotiation_session.domain.events import SimulationRunOpened
from negotiation_session.domain.simulation_run import SimulationRun
from negotiation_session.domain.values import (
    ArgumentStance,
    ClaimEvidence,
    CoalitionId,
    ConsensusLevel,
    EvidencePackId,
    LearningId,
    MandateId,
    NegotiationPhase,
    Proposal,
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
    run.submit_initial_position(
        STAKEHOLDER_A,
        TOPIC,
        ArgumentStance.SUPPORT,
        Proposal(summary="A"),
        [ClaimEvidence(EvidencePackId("pack_1"), "psg_1", "support")],
    )
    return run


def test_closing_keeps_the_whole_event_log_for_replay() -> None:
    run = _run()
    before = list(run.events)
    run.advance_phase(NegotiationPhase.CLOSED)
    after = list(run.events)
    assert after[: len(before)] == before
    assert isinstance(after[0], SimulationRunOpened)
    assert len(after) == len(before) + 1
    assert run.drain_events() == after


def test_a_closed_run_refuses_terminal_evaluation_and_coalitions() -> None:
    run = _run()
    run.advance_phase(NegotiationPhase.CLOSED)
    with pytest.raises(ClosedRunImmutable):
        run.evaluate_stopping(ConsensusLevel.SUFFICIENT)
    with pytest.raises(ClosedRunImmutable):
        run.form_coalition(
            topic=TOPIC,
            member_ids=(STAKEHOLDER_A,),
            proposal=Proposal(summary="Shared"),
            coalition_id=CoalitionId("coa_1"),
        )
    assert run.is_closed


def test_close_round_is_refused_after_closure() -> None:
    run = _run()
    run.advance_phase(NegotiationPhase.CLOSED)
    with pytest.raises(ClosedRunImmutable):
        run.close_round(RoundLearning(LearningId("lrn_1"), 1))
