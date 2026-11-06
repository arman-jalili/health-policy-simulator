"""Contract freeze: coalition offer (issue #282, implements #293)."""

from __future__ import annotations

from tests.unit.negotiation_session_contract_helpers import (
    field_names,
    method_names,
    parameter_names,
)

from negotiation_session.application.services import FormCoalition
from negotiation_session.domain.entities import Coalition, CoalitionOffer
from negotiation_session.domain.errors import (
    CoalitionWithoutOffer,
    InvalidCoalitionOfferTransition,
)
from negotiation_session.domain.events import (
    CoalitionFormed,
    CoalitionOfferDeclined,
    CoalitionOffered,
)
from negotiation_session.domain.simulation_run import SimulationRun


def test_membership_requires_a_recorded_offer() -> None:
    assert field_names(Coalition) == ["id", "topic", "proposal", "members", "offers"]
    assert parameter_names(Coalition.form) == ["coalition_id", "topic", "proposal", "offers"]
    assert "add_member" in method_names(Coalition)
    assert CoalitionWithoutOffer.code == "COALITION_WITHOUT_OFFER"


def test_offer_lifecycle_is_offered_then_accepted_or_declined() -> None:
    assert field_names(CoalitionOffer)[:5] == [
        "id",
        "coalition_id",
        "invited",
        "conditions",
        "status",
    ]
    assert parameter_names(CoalitionOffer.offer) == [
        "offer_id",
        "coalition_id",
        "invited",
        "conditions",
    ]
    assert parameter_names(CoalitionOffer.decline) == ["self", "reason"]
    assert InvalidCoalitionOfferTransition.code == "INVALID_COALITION_OFFER_TRANSITION"


def test_coalitions_publish_offers_and_membership() -> None:
    assert field_names(CoalitionOffered) == [
        "run_id",
        "coalition_id",
        "invited_id",
        "conditions",
    ]
    assert field_names(CoalitionOfferDeclined) == [
        "run_id",
        "coalition_id",
        "stakeholder_id",
        "reason",
    ]
    assert field_names(CoalitionFormed) == [
        "run_id",
        "topic",
        "coalition_id",
        "members",
        "proposal",
    ]
    assert parameter_names(SimulationRun.form_coalition) == [
        "self",
        "topic",
        "member_ids",
        "proposal",
        "coalition_id",
    ]
    assert parameter_names(FormCoalition.execute) == ["self", "request"]
