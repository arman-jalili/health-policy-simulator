"""Behaviour of the stopping conditions and round cap (issue #292)."""

from __future__ import annotations

import pytest

from negotiation_session.domain.entities import NegotiationMandate, RoundLearning
from negotiation_session.domain.errors import RoundCapExceeded
from negotiation_session.domain.events import SimulationRunClosed
from negotiation_session.domain.services import EvaluateStoppingCondition
from negotiation_session.domain.simulation_run import SimulationRun
from negotiation_session.domain.values import (
    ConsensusLevel,
    LearningId,
    MandateId,
    NegotiationPhase,
    RunId,
    StakeholderBinding,
    StakeholderId,
    StoppingCondition,
    StoppingConditionName,
    TopicRef,
)

STAKEHOLDER_A = StakeholderId("stk_a")
STAKEHOLDER_B = StakeholderId("stk_b")
TOPIC = TopicRef("costs")


def _run(round_cap: int = 5) -> SimulationRun:
    return SimulationRun.open(
        run_id=RunId("run_1"),
        mandate=NegotiationMandate(
            id=MandateId("mnd_1"),
            question="How to stabilise costs?",
            objective="Agreement",
            constraints=(),
            round_cap=round_cap,
            stopping_conditions=(StoppingConditionName.CONSENSUS,),
            profile_version="v1",
        ),
        bound={
            STAKEHOLDER_A: StakeholderBinding(STAKEHOLDER_A, "A", "A"),
            STAKEHOLDER_B: StakeholderBinding(STAKEHOLDER_B, "B", "B"),
        },
    )


def _close_round(run: SimulationRun, number: int) -> None:
    run.open_round()
    run.record_abstention(STAKEHOLDER_A, TOPIC)
    run.record_abstention(STAKEHOLDER_B, TOPIC)
    run.close_round(RoundLearning(LearningId(f"lrn_{number}"), number))


def test_consensus_fires_before_the_cap() -> None:
    condition = StoppingCondition.evaluate(
        consensus=ConsensusLevel.SUFFICIENT,
        rounds_done=1,
        round_cap=5,
        deadlocked=True,
    )
    assert condition.name is StoppingConditionName.CONSENSUS
    assert condition.fired


def test_the_cap_fires_before_deadlock() -> None:
    condition = EvaluateStoppingCondition().evaluate(
        consensus=ConsensusLevel.NONE,
        rounds_done=5,
        round_cap=5,
        deadlocked=True,
    )
    assert condition.name is StoppingConditionName.ROUND_CAP
    assert condition.fired


def test_deadlock_fires_when_nothing_else_does() -> None:
    condition = EvaluateStoppingCondition().evaluate(
        consensus=ConsensusLevel.EMERGING,
        rounds_done=2,
        round_cap=5,
        deadlocked=True,
    )
    assert condition.name is StoppingConditionName.DEADLOCK
    assert condition.fired


def test_no_condition_fires_mid_run() -> None:
    condition = EvaluateStoppingCondition().evaluate(
        consensus=ConsensusLevel.NONE,
        rounds_done=2,
        round_cap=5,
        deadlocked=False,
    )
    assert not condition.fired


def test_consensus_closes_the_run_and_publishes_the_terminal_event() -> None:
    run = _run()
    run.open_round()
    condition = run.evaluate_stopping(ConsensusLevel.SUFFICIENT)
    assert condition.fired
    assert run.phase is NegotiationPhase.CLOSED
    closed = [event for event in run.events if isinstance(event, SimulationRunClosed)]
    assert len(closed) == 1
    assert closed[0].condition is StoppingConditionName.CONSENSUS


def test_the_sixth_open_round_forces_terminal_evaluation() -> None:
    run = _run(round_cap=5)
    for number in range(1, 6):
        _close_round(run, number)
    assert len(run.rounds) == 5
    with pytest.raises(RoundCapExceeded):
        run.open_round()
    assert run.is_closed
    closed = [event for event in run.events if isinstance(event, SimulationRunClosed)]
    assert len(closed) == 1
    assert closed[0].condition is StoppingConditionName.ROUND_CAP
    assert closed[0].rounds == 5
    assert closed[0].final_phase is NegotiationPhase.CLOSED
