"""Behaviour of coalition offers and membership (issue #293)."""

from __future__ import annotations

import pytest

from negotiation_session.domain.entities import (
    Coalition,
    CoalitionOffer,
    NegotiationMandate,
)
from negotiation_session.domain.errors import (
    CoalitionWithoutOffer,
    InvalidCoalitionOfferTransition,
    StakeholderNotBound,
)
from negotiation_session.domain.events import CoalitionFormed, CoalitionOffered
from negotiation_session.domain.simulation_run import SimulationRun
from negotiation_session.domain.values import (
    CoalitionId,
    CoalitionOfferId,
    CoalitionOfferStatus,
    MandateId,
    Proposal,
    RunId,
    StakeholderBinding,
    StakeholderId,
    StoppingConditionName,
    TopicRef,
)

STAKEHOLDER_A = StakeholderId("stk_a")
STAKEHOLDER_B = StakeholderId("stk_b")
STAKEHOLDER_C = StakeholderId("stk_c")
TOPIC = TopicRef("costs")
COALITION = CoalitionId("coa_1")


def _offer(invited: StakeholderId, offered: bool = True) -> CoalitionOffer:
    offer = CoalitionOffer.offer(
        offer_id=CoalitionOfferId(f"cfo_{invited}"),
        coalition_id=COALITION,
        invited=invited,
        conditions="shared proposal",
    )
    if offered:
        offer.accept()
    return offer


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
            stakeholder: StakeholderBinding(stakeholder, stakeholder, stakeholder)
            for stakeholder in (STAKEHOLDER_A, STAKEHOLDER_B)
        },
    )
    run.open_round()
    return run


def test_offer_moves_from_offered_to_accepted_once() -> None:
    offer = _offer(STAKEHOLDER_A, offered=False)
    assert offer.status is CoalitionOfferStatus.OFFERED
    offer.accept()
    assert offer.status.value == CoalitionOfferStatus.ACCEPTED.value
    with pytest.raises(InvalidCoalitionOfferTransition):
        offer.accept()


def test_offer_decline_records_the_reason_and_blocks_acceptance() -> None:
    offer = _offer(STAKEHOLDER_A, offered=False)
    offer.decline("no mandate")
    assert offer.status.value == CoalitionOfferStatus.DECLINED.value
    assert offer.decline_reason == "no mandate"
    with pytest.raises(InvalidCoalitionOfferTransition):
        offer.accept()


def test_a_coalition_cannot_add_a_stakeholder_without_an_accepted_offer() -> None:
    coalition = Coalition.form(
        coalition_id=COALITION,
        topic=TOPIC,
        proposal=Proposal(summary="Shared"),
        offers={STAKEHOLDER_A: _offer(STAKEHOLDER_A)},
    )
    assert coalition.members == [STAKEHOLDER_A]
    with pytest.raises(CoalitionWithoutOffer):
        coalition.add_member(STAKEHOLDER_B)
    pending = Coalition.form(
        coalition_id=COALITION,
        topic=TOPIC,
        proposal=Proposal(summary="Shared"),
        offers={STAKEHOLDER_B: _offer(STAKEHOLDER_B, offered=False)},
    )
    with pytest.raises(CoalitionWithoutOffer):
        pending.add_member(STAKEHOLDER_B)


def test_only_accepted_offers_become_members() -> None:
    coalition = Coalition.form(
        coalition_id=COALITION,
        topic=TOPIC,
        proposal=Proposal(summary="Shared"),
        offers={
            STAKEHOLDER_A: _offer(STAKEHOLDER_A),
            STAKEHOLDER_B: _offer(STAKEHOLDER_B, offered=False),
        },
    )
    assert coalition.members == [STAKEHOLDER_A]


def test_the_aggregate_records_offers_before_forming_the_coalition() -> None:
    run = _run()
    coalition = run.form_coalition(
        topic=TOPIC,
        member_ids=(STAKEHOLDER_A, STAKEHOLDER_B),
        proposal=Proposal(summary="Shared"),
        coalition_id=COALITION,
    )
    assert run.coalitions[COALITION] is coalition
    assert coalition.members == [STAKEHOLDER_A, STAKEHOLDER_B]
    assert all(offer.status is CoalitionOfferStatus.ACCEPTED for offer in coalition.offers.values())
    offered = [event for event in run.events if isinstance(event, CoalitionOffered)]
    formed = [event for event in run.events if isinstance(event, CoalitionFormed)]
    assert len(offered) == 2
    assert len(formed) == 1
    assert formed[0].members == (STAKEHOLDER_A, STAKEHOLDER_B)


def test_an_unbound_stakeholder_cannot_join() -> None:
    run = _run()
    with pytest.raises(StakeholderNotBound):
        run.form_coalition(
            topic=TOPIC,
            member_ids=(STAKEHOLDER_C,),
            proposal=Proposal(summary="Shared"),
            coalition_id=COALITION,
        )
