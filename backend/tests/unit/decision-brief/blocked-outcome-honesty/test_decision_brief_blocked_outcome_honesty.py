"""Contract freeze: blocked-outcome honesty (issue #331, implements #347).

A veto-blocked topic has its own rendering state and can never be a recommendation.
"""

from __future__ import annotations

from tests.unit.decision_brief_contract_helpers import field_names, parameter_names

from decision_brief.domain.errors import BlockedOutcomeMisrendered
from decision_brief.domain.services import OutcomeHonestyPolicy
from decision_brief.domain.values import OutcomeKind, TopicOutcome


def test_outcome_kinds_separate_recommendations_from_blocked_topics() -> None:
    assert {member.value for member in OutcomeKind} == {
        "recommendation",
        "blocked",
        "open_dispute",
    }


def test_topic_outcome_fields_are_frozen() -> None:
    assert field_names(TopicOutcome) == [
        "topic",
        "kind",
        "blocking_stakeholders",
        "reason",
    ]


def test_a_blocked_topic_keeps_its_blockers() -> None:
    outcome = TopicOutcome(
        topic="Single payer fund",
        kind=OutcomeKind.BLOCKED,
        blocking_stakeholders=("Ärztekammer",),
        reason="veto right",
    )
    assert outcome.kind is OutcomeKind.BLOCKED
    assert outcome.blocking_stakeholders == ("Ärztekammer",)


def test_misrendering_a_blocked_topic_is_its_own_failure() -> None:
    error = BlockedOutcomeMisrendered("Single payer fund")
    assert error.code == "BLOCKED_OUTCOME_MISRENDERED"
    assert error.status_code == 422
    assert error.topic == "Single payer fund"


def test_the_honesty_policy_is_a_domain_contract() -> None:
    assert parameter_names(OutcomeHonestyPolicy.assert_honest) == ["self", "outcomes"]
