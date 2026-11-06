"""Contract freeze and aggregate behaviour of ``SimulationRun`` (issues #282, #283)."""

from __future__ import annotations

import pytest
from tests.unit.negotiation_session_contract_helpers import field_names, parameter_names

from negotiation_session.domain.entities import NegotiationMandate, RoundLearning
from negotiation_session.domain.errors import (
    ClosedRunImmutable,
    PhaseRegression,
    RevisionWithoutCause,
    RoundCloseGuardViolation,
    RoundStillOpen,
)
from negotiation_session.domain.events import (
    InitialPositionStated,
    PositionRevised,
    PositionRevisionRejected,
    SimulationRunOpened,
)
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


def _mandate(round_cap: int = 5) -> NegotiationMandate:
    return NegotiationMandate(
        id=MandateId("mnd_1"),
        question="How to stabilise costs?",
        objective="Agreement on measures",
        constraints=(),
        round_cap=round_cap,
        stopping_conditions=(StoppingConditionName.CONSENSUS,),
        profile_version="v1",
        mandate_hash="hash_1",
    )


def _binding(stakeholder: StakeholderId) -> StakeholderBinding:
    return StakeholderBinding(
        stakeholder_id=stakeholder,
        institution_name=stakeholder,
        institution_code=stakeholder,
    )


def _run(round_cap: int = 5) -> SimulationRun:
    return SimulationRun.open(
        run_id=RunId("run_1"),
        mandate=_mandate(round_cap),
        bound={
            STAKEHOLDER_A: _binding(STAKEHOLDER_A),
            STAKEHOLDER_B: _binding(STAKEHOLDER_B),
        },
    )


def _evidence(pack: str = "pack_1") -> ClaimEvidence:
    return ClaimEvidence(
        evidence_id=EvidencePackId(pack),
        passage_id="psg_1",
        stance="support",
    )


def _proposal(summary: str = "Increase the deductible") -> Proposal:
    return Proposal(summary=summary)


def _learning(round_number: int = 1) -> RoundLearning:
    return RoundLearning(id=LearningId(f"lrn_{round_number}"), round_number=round_number)


def test_aggregate_fields_are_frozen() -> None:
    assert field_names(SimulationRun) == [
        "id",
        "mandate",
        "phase",
        "round_cap",
        "bound",
        "rounds",
        "conflicts",
        "coalitions",
        "events",
    ]


def test_aggregate_exposes_the_frozen_command_surface() -> None:
    for name in (
        "open",
        "open_round",
        "submit_initial_position",
        "take_turn",
        "revise_position",
        "record_abstention",
        "track_conflict",
        "form_coalition",
        "close_round",
        "evaluate_stopping",
        "advance_phase",
        "turn_order",
        "drain_events",
        "open_position",
        "position_by_id",
    ):
        assert callable(getattr(SimulationRun, name)), name
    assert isinstance(vars(SimulationRun)["is_closed"], property)
    assert isinstance(vars(SimulationRun)["current_round"], property)


def test_factory_and_turn_signatures_are_frozen() -> None:
    assert parameter_names(SimulationRun.open) == ["run_id", "mandate", "bound"]
    assert parameter_names(SimulationRun.open_round) == ["self"]
    assert parameter_names(SimulationRun.take_turn) == [
        "self",
        "stakeholder",
        "target",
        "stance",
        "text",
        "claims",
        "evidence",
        "unsupported",
        "invocation_id",
    ]


# ── AC 1: phase monotonicity ────────────────────────────────────────────────


def test_open_binds_stakeholders_and_emits_the_opening_event() -> None:
    run = _run()
    assert run.phase is NegotiationPhase.POSITION_FORMATION
    events = run.drain_events()
    assert [type(event) for event in events] == [SimulationRunOpened]
    assert run.drain_events() == []


def test_open_round_after_closed_is_refused_and_phase_never_regresses() -> None:
    run = _run()
    run.open_round()
    run.advance_phase(NegotiationPhase.DEBATE)
    with pytest.raises(PhaseRegression):
        run.advance_phase(NegotiationPhase.POSITION_FORMATION)
    run.advance_phase(NegotiationPhase.CLOSED)
    assert run.is_closed
    with pytest.raises(ClosedRunImmutable):
        run.open_round()
    assert run.phase is NegotiationPhase.CLOSED


def test_a_round_cannot_be_opened_twice() -> None:
    run = _run()
    run.open_round()
    with pytest.raises(RoundStillOpen):
        run.open_round()


# ── AC 2: round close guard ─────────────────────────────────────────────────


def test_close_round_refuses_an_unaccounted_stakeholder() -> None:
    run = _run()
    run.open_round()
    run.submit_initial_position(
        STAKEHOLDER_A, TOPIC, ArgumentStance.SUPPORT, _proposal(), [_evidence()]
    )
    with pytest.raises(RoundCloseGuardViolation):
        run.close_round(_learning())


def test_close_round_succeeds_when_everyone_spoke_or_abstained() -> None:
    run = _run()
    round_ = run.open_round()
    run.submit_initial_position(
        STAKEHOLDER_A, TOPIC, ArgumentStance.SUPPORT, _proposal(), [_evidence()]
    )
    run.record_abstention(STAKEHOLDER_B, TOPIC)
    run.close_round(_learning())
    assert round_.is_closed
    assert round_.learning is not None


# ── AC 3: revision without cause ────────────────────────────────────────────


def test_revision_without_cause_is_rejected_and_changes_no_state() -> None:
    run = _run()
    run.open_round()
    position = run.submit_initial_position(
        STAKEHOLDER_A, TOPIC, ArgumentStance.SUPPORT, _proposal(), [_evidence()]
    )
    seen = len(run.events)
    with pytest.raises(RevisionWithoutCause):
        run.revise_position(STAKEHOLDER_A, TOPIC, ArgumentStance.OPPOSE, RevisionReason())
    assert run.open_position(STAKEHOLDER_A, TOPIC).stance is ArgumentStance.SUPPORT
    rejected = [event for event in run.events[seen:] if isinstance(event, PositionRevisionRejected)]
    assert len(rejected) == 1
    assert rejected[0].reason_code == RevisionWithoutCause.code
    assert position.is_open


def test_revision_with_a_cited_argument_supersedes_the_position() -> None:
    run = _run()
    run.open_round()
    original = run.submit_initial_position(
        STAKEHOLDER_A, TOPIC, ArgumentStance.SUPPORT, _proposal(), [_evidence()]
    )
    argument = run.take_turn(
        STAKEHOLDER_A,
        TargetRef(topic=TOPIC),
        ArgumentStance.QUALIFY,
        "The figures changed.",
        (),
        [_evidence("pack_2")],
    )
    revised = run.revise_position(
        STAKEHOLDER_A,
        TOPIC,
        ArgumentStance.OPPOSE,
        RevisionReason(argument_ids=(argument.id,), driver="new evidence"),
    )
    assert revised.stance is ArgumentStance.OPPOSE
    assert revised.supersedes == original.id
    assert not original.is_open
    assert any(isinstance(event, PositionRevised) for event in run.events)


# ── AC 4: one open position ─────────────────────────────────────────────────


def test_a_second_initial_position_supersedes_instead_of_duplicating() -> None:
    run = _run()
    run.open_round()
    first = run.submit_initial_position(
        STAKEHOLDER_A, TOPIC, ArgumentStance.SUPPORT, _proposal("A"), [_evidence()]
    )
    second = run.submit_initial_position(
        STAKEHOLDER_A, TOPIC, ArgumentStance.OPPOSE, _proposal("B"), [_evidence("pack_2")]
    )
    assert second.supersedes == first.id
    assert first.superseded_by == second.id
    assert not first.is_open
    assert second.is_open
    open_positions = [
        position
        for position in run.current_round.positions.values()
        if position.is_open and position.stakeholder == STAKEHOLDER_A
    ]
    assert len(open_positions) == 1
    assert open_positions[0].id == second.id
    stated = [event for event in run.events if isinstance(event, InitialPositionStated)]
    assert len(stated) == 2
