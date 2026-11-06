"""Behaviour of the one-open-position invariant (issue #289)."""

from __future__ import annotations

from negotiation_session.domain.entities import NegotiationMandate, Position
from negotiation_session.domain.simulation_run import SimulationRun
from negotiation_session.domain.values import (
    ArgumentStance,
    ClaimEvidence,
    EvidencePackId,
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
    return run


def _evidence(pack: str = "pack_1") -> ClaimEvidence:
    return ClaimEvidence(EvidencePackId(pack), "psg_1", "support")


def _submit(run: SimulationRun, summary: str) -> Position:
    return run.submit_initial_position(
        STAKEHOLDER_A, TOPIC, ArgumentStance.SUPPORT, Proposal(summary=summary), [_evidence()]
    )


def test_a_second_initial_position_is_a_new_open_entry() -> None:
    run = _run()
    first = _submit(run, "A")
    second = _submit(run, "B")
    assert first.is_open is False
    assert second.is_open is True
    assert second.supersedes == first.id
    assert run.open_position(STAKEHOLDER_A, TOPIC) is second
    open_entries = [
        position
        for position in run.current_round.positions.values()
        if position.is_open and position.stakeholder == STAKEHOLDER_A
    ]
    assert len(open_entries) == 1


def test_stakeholders_keep_independent_open_positions() -> None:
    run = _run()
    first = _submit(run, "A")
    other = run.submit_initial_position(
        STAKEHOLDER_B, TOPIC, ArgumentStance.OPPOSE, Proposal(summary="B"), [_evidence("pack_2")]
    )
    assert first.is_open
    assert other.is_open
    open_entries = [
        position for position in run.current_round.positions.values() if position.is_open
    ]
    assert len(open_entries) == 2


def test_a_revision_chain_keeps_exactly_one_open_entry() -> None:
    run = _run()
    original = _submit(run, "A")
    argument = run.take_turn(
        STAKEHOLDER_A,
        TargetRef(topic=TOPIC),
        ArgumentStance.QUALIFY,
        "Evidence changed.",
        (),
        [_evidence("pack_2")],
    )
    reason = RevisionReason(argument_ids=(argument.id,), driver="evidence")
    first_revision = run.revise_position(STAKEHOLDER_A, TOPIC, ArgumentStance.QUALIFY, reason)
    second_revision = run.revise_position(STAKEHOLDER_A, TOPIC, ArgumentStance.OPPOSE, reason)
    history = [
        position
        for position in run.current_round.positions.values()
        if position.stakeholder == STAKEHOLDER_A
    ]
    assert len(history) == 1
    assert history[0] is second_revision
    assert first_revision.supersedes == original.id
    assert second_revision.supersedes == first_revision.id
    assert not original.is_open
    assert not first_revision.is_open
    assert second_revision.is_open
    assert run.open_position(STAKEHOLDER_A, TOPIC) is second_revision
