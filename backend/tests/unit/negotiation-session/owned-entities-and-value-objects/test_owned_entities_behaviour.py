"""Behaviour of owned entities and value objects (issue #284)."""

from __future__ import annotations

from decimal import Decimal

from negotiation_session.domain.entities import Argument, ConflictTopic, NegotiationMandate
from negotiation_session.domain.events import ConflictTopicOpened
from negotiation_session.domain.services import DetectArgumentContradiction
from negotiation_session.domain.simulation_run import SimulationRun
from negotiation_session.domain.values import (
    ArgumentId,
    ArgumentStance,
    ConflictStatus,
    ConflictTopicId,
    MandateId,
    Proposal,
    ProposalComponent,
    ProposalQuantification,
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


def _mandate() -> NegotiationMandate:
    return NegotiationMandate(
        id=MandateId("mnd_1"),
        question="How to stabilise costs?",
        objective="Agreement on measures",
        constraints=(),
        round_cap=5,
        stopping_conditions=(StoppingConditionName.CONSENSUS,),
        profile_version="v1",
    )


def _run() -> SimulationRun:
    return SimulationRun.open(
        run_id=RunId("run_1"),
        mandate=_mandate(),
        bound={
            STAKEHOLDER_A: StakeholderBinding(STAKEHOLDER_A, "A", "A"),
            STAKEHOLDER_B: StakeholderBinding(STAKEHOLDER_B, "B", "B"),
        },
    )


def _argument(stakeholder: StakeholderId, stance: ArgumentStance) -> Argument:
    return Argument.new(
        argument_id=ArgumentId(f"arg_{stakeholder}"),
        stakeholder=stakeholder,
        target=TargetRef(topic=TOPIC),
        stance=stance,
        text="text",
        claims=(),
        evidence=(),
        unsupported=True,
        round_number=1,
    )


def test_component_is_admissible_for_impact_only_when_quantified() -> None:
    quantified = ProposalComponent(
        measure="Raise the deductible",
        effect="-2% spend",
        population="All insured",
        cost_eur=Decimal("1000"),
        quantification=ProposalQuantification.QUANTIFIED,
    )
    unquantified = ProposalComponent(
        measure="Better coordination",
        effect="unknown",
        population="All insured",
        quantification=ProposalQuantification.UNQUANTIFIED,
    )
    assert quantified.is_admissible_for_impact()
    assert not unquantified.is_admissible_for_impact()

    proposal = Proposal(summary="Package", components=(quantified, unquantified))
    assert proposal.quantified_components() == (quantified,)
    assert not proposal.is_fully_quantified()
    assert Proposal(summary="Empty").is_fully_quantified()


def test_mandate_is_immutable_after_the_run_opens() -> None:
    mandate = _mandate()
    assert not mandate.is_immutable_after_open()
    SimulationRun.open(
        run_id=RunId("run_2"),
        mandate=mandate,
        bound={STAKEHOLDER_A: StakeholderBinding(STAKEHOLDER_A, "A", "A")},
    )
    assert mandate.is_immutable_after_open()


def test_conflict_topic_keeps_a_stance_history() -> None:
    conflict = ConflictTopic.open(
        conflict_id=ConflictTopicId("cft_1"),
        topic=TOPIC,
        stances={STAKEHOLDER_A: ArgumentStance.SUPPORT, STAKEHOLDER_B: ArgumentStance.OPPOSE},
    )
    assert conflict.status is ConflictStatus.OPEN
    conflict.record_stance(STAKEHOLDER_A, ArgumentStance.QUALIFY, round_number=2)
    assert conflict.stances[STAKEHOLDER_A] is ArgumentStance.QUALIFY
    assert (2, STAKEHOLDER_A, ArgumentStance.QUALIFY) in conflict.history


def test_track_conflict_publishes_the_event_and_keeps_the_topic() -> None:
    run = _run()
    run.open_round()
    conflict = run.track_conflict(
        TOPIC, {STAKEHOLDER_A: ArgumentStance.SUPPORT, STAKEHOLDER_B: ArgumentStance.OPPOSE}
    )
    assert run.conflicts[TOPIC] is conflict
    assert any(isinstance(event, ConflictTopicOpened) for event in run.events)
    assert conflict.stances[STAKEHOLDER_B] is ArgumentStance.OPPOSE


def test_contradiction_detector_flags_opposing_stances_on_one_topic() -> None:
    support = _argument(STAKEHOLDER_A, ArgumentStance.SUPPORT)
    oppose = _argument(STAKEHOLDER_B, ArgumentStance.OPPOSE)
    detector = DetectArgumentContradiction()
    assert detector.contradicts(support, oppose)
    assert not detector.contradicts(support, support)
    findings = detector.detect([support, oppose])
    assert len(findings) == 1
    assert findings[0].topic == TOPIC
    assert {findings[0].argument_id_a, findings[0].argument_id_b} == {support.id, oppose.id}
