"""Behaviour of turn discipline and turn-order policy (issue #291)."""

from __future__ import annotations

import pytest

from negotiation_session.domain.entities import NegotiationMandate
from negotiation_session.domain.errors import DuplicateTurn
from negotiation_session.domain.services import (
    AffectedFirstTurnOrder,
    PowerWeightedTurnOrder,
    RoundRobinTurnOrder,
)
from negotiation_session.domain.simulation_run import SimulationRun
from negotiation_session.domain.values import (
    ArgumentStance,
    ClaimEvidence,
    EvidencePackId,
    MandateId,
    RunId,
    StakeholderBinding,
    StakeholderId,
    StoppingConditionName,
    TargetRef,
    TopicRef,
    TurnOutcome,
)

STAKEHOLDER_A = StakeholderId("stk_a")
STAKEHOLDER_B = StakeholderId("stk_b")
TOPIC = TopicRef("costs")


def _binding(
    stakeholder: StakeholderId,
    *,
    vetoes: int = 0,
    interests: int = 0,
    mandate_topics: tuple[TopicRef, ...] = (),
) -> StakeholderBinding:
    return StakeholderBinding(
        stakeholder,
        stakeholder,
        stakeholder,
        interests=tuple(f"i{index}" for index in range(interests)),
        veto_classes=tuple(f"v{index}" for index in range(vetoes)),
        mandate_topics=mandate_topics,
    )


def _bound() -> dict[StakeholderId, StakeholderBinding]:
    return {
        STAKEHOLDER_A: _binding(STAKEHOLDER_A, vetoes=1, interests=1, mandate_topics=(TOPIC,)),
        STAKEHOLDER_B: _binding(STAKEHOLDER_B, interests=4),
    }


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
        bound=_bound(),
    )
    run.open_round()
    return run


def _evidence(pack: str = "pack_1") -> ClaimEvidence:
    return ClaimEvidence(EvidencePackId(pack), "psg_1", "support")


def _turn(run: SimulationRun, stakeholder: StakeholderId, topic: TopicRef = TOPIC) -> None:
    run.take_turn(
        stakeholder,
        TargetRef(topic=topic),
        ArgumentStance.SUPPORT,
        "text",
        (),
        [_evidence()],
    )


def test_a_duplicate_turn_on_the_same_topic_is_refused() -> None:
    run = _run()
    _turn(run, STAKEHOLDER_A)
    with pytest.raises(DuplicateTurn):
        _turn(run, STAKEHOLDER_A)


def test_a_different_topic_in_the_same_round_is_allowed() -> None:
    run = _run()
    _turn(run, STAKEHOLDER_A)
    _turn(run, STAKEHOLDER_A, TopicRef("access"))
    assert len(run.current_round.arguments) == 2


def test_an_abstention_blocks_a_later_turn_on_the_same_topic() -> None:
    run = _run()
    run.record_abstention(STAKEHOLDER_A, TOPIC)
    with pytest.raises(DuplicateTurn):
        _turn(run, STAKEHOLDER_A)


def test_every_strategy_assigns_every_bound_stakeholder_once() -> None:
    bound = _bound()
    for strategy in (
        RoundRobinTurnOrder(),
        PowerWeightedTurnOrder(),
        AffectedFirstTurnOrder(),
    ):
        assignments = strategy.assign(bound=bound, round_number=1, topics=(TOPIC,))
        assert [assignment.stakeholder for assignment in assignments] == sorted(bound)
        assert [assignment.order for assignment in assignments] == [0, 1]
        assert all(assignment.outcome is TurnOutcome.PENDING for assignment in assignments)


def test_power_weighted_puts_the_stronger_veto_first() -> None:
    assignments = PowerWeightedTurnOrder().assign(bound=_bound(), round_number=1, topics=(TOPIC,))
    assert assignments[0].stakeholder == STAKEHOLDER_A


def test_affected_first_puts_actors_with_a_mandate_covering_the_topic_first() -> None:
    assignments = AffectedFirstTurnOrder().assign(bound=_bound(), round_number=1, topics=(TOPIC,))
    assert assignments[0].stakeholder == STAKEHOLDER_A


def test_the_aggregate_uses_the_round_robin_policy_and_records_outcomes() -> None:
    run = _run()
    assert [assignment.stakeholder for assignment in run.turn_order()] == [
        STAKEHOLDER_A,
        STAKEHOLDER_B,
    ]
    _turn(run, STAKEHOLDER_A)
    assert run.current_round.turn_order[0].outcome is TurnOutcome.SPOKE
    assert run.current_round.turn_order[1].outcome is TurnOutcome.PENDING
