"""Contract freeze and outcome honesty (issue #331, implements #343).

A veto-blocked topic has its own rendering state and can never be a recommendation.
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from tests.unit.decision_brief_contract_helpers import field_names, parameter_names

from decision_brief.domain.decision_brief import DecisionBrief
from decision_brief.domain.entities import BriefSection
from decision_brief.domain.errors import BlockedOutcomeMisrendered
from decision_brief.domain.services import OutcomeHonestyCheck, OutcomeHonestyPolicy
from decision_brief.domain.values import (
    DEFAULT_DISCLAIMER_TEXT,
    SECTION_ORDINAL,
    BriefId,
    BriefStatus,
    BriefVersion,
    CitedStatement,
    EvidenceStatus,
    OutcomeKind,
    RunId,
    SectionKind,
    SimulationDisclaimer,
    TopicOutcome,
)
from decision_brief.interfaces.http.schemas import TopicOutcomeBody


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


# ── A vetoed topic is stated as blocked, never as a recommendation (#343) ───────────

DISCLAIMER = SimulationDisclaimer(
    text=DEFAULT_DISCLAIMER_TEXT,
    model_reference="openai/gpt-5.1",
    prompt_version="brief.v3",
)


def test_a_blocked_topic_states_itself_honestly() -> None:
    TopicOutcome(
        topic="Single payer fund",
        kind=OutcomeKind.BLOCKED,
        blocking_stakeholders=("Ärztekammer",),
    ).assert_honest()


def test_a_vetoed_topic_rendered_as_a_recommendation_is_refused() -> None:
    outcome = TopicOutcome(
        topic="Single payer fund",
        kind=OutcomeKind.RECOMMENDATION,
        blocking_stakeholders=("Ärztekammer",),
    )

    with pytest.raises(BlockedOutcomeMisrendered) as raised:
        outcome.assert_honest()

    assert raised.value.topic == "Single payer fund"


@pytest.mark.parametrize("kind", [OutcomeKind.RECOMMENDATION, OutcomeKind.OPEN_DISPUTE])
def test_a_vetoed_topic_cannot_be_stated_as_anything_but_blocked(kind: OutcomeKind) -> None:
    with pytest.raises(BlockedOutcomeMisrendered):
        TopicOutcome(
            topic="Single payer fund",
            kind=kind,
            blocking_stakeholders=("Ärztekammer",),
        ).assert_honest()


def test_the_policy_accepts_an_honest_outcome_list() -> None:
    OutcomeHonestyCheck().assert_honest(
        [
            TopicOutcome(topic="Waiting times", kind=OutcomeKind.RECOMMENDATION),
            TopicOutcome(
                topic="Single payer fund",
                kind=OutcomeKind.BLOCKED,
                blocking_stakeholders=("Ärztekammer",),
            ),
            TopicOutcome(topic="Private hospitals", kind=OutcomeKind.OPEN_DISPUTE),
        ]
    )


def test_the_policy_names_the_first_misrendered_topic() -> None:
    with pytest.raises(BlockedOutcomeMisrendered) as raised:
        OutcomeHonestyCheck().assert_honest(
            [
                TopicOutcome(topic="Waiting times", kind=OutcomeKind.RECOMMENDATION),
                TopicOutcome(
                    topic="Single payer fund",
                    kind=OutcomeKind.RECOMMENDATION,
                    blocking_stakeholders=("Ärztekammer",),
                ),
            ]
        )
    assert raised.value.topic == "Single payer fund"


def _brief(outcomes: tuple[TopicOutcome, ...]) -> DecisionBrief:
    statement = CitedStatement(text="Waiting times rose.", status=EvidenceStatus.NARRATIVE)
    return DecisionBrief(
        id=BriefId("brf_01J"),
        run_id=RunId("run_01J"),
        version=BriefVersion(
            number=1,
            run_id=RunId("run_01J"),
            snapshot_ref="snap_01J",
            generated_at=datetime(2026, 11, 6, tzinfo=UTC),
        ),
        sections={
            kind: BriefSection(
                kind=kind,
                ordinal=SECTION_ORDINAL[kind],
                statements=(statement,) if kind is SectionKind.QUESTION else (),
            )
            for kind in SectionKind
        },
        outcomes=outcomes,
        disclaimer=DISCLAIMER,
    )


def test_publication_blocks_a_misrendered_outcome() -> None:
    brief = _brief(
        (
            TopicOutcome(
                topic="Single payer fund",
                kind=OutcomeKind.RECOMMENDATION,
                blocking_stakeholders=("Ärztekammer",),
            ),
        )
    )

    with pytest.raises(BlockedOutcomeMisrendered):
        brief.publish()

    assert brief.status is BriefStatus.BLOCKED
    assert brief.is_published() is False


def test_publication_accepts_honest_blocked_outcomes() -> None:
    brief = _brief(
        (
            TopicOutcome(
                topic="Single payer fund",
                kind=OutcomeKind.BLOCKED,
                blocking_stakeholders=("Ärztekammer",),
            ),
        )
    )

    brief.publish()

    assert brief.status is BriefStatus.PUBLISHED


def test_the_wire_kind_admits_blocked() -> None:
    body = TopicOutcomeBody(
        topic="Single payer fund",
        kind="blocked",
        blocking_stakeholders=["Ärztekammer"],
    )
    assert body.model_dump()["kind"] == "blocked"
