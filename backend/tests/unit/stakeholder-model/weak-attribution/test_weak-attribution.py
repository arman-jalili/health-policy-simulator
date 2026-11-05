"""Contract freeze: attribution strength governs position usability."""

from __future__ import annotations

import inspect
from datetime import date
from decimal import Decimal

from tests.unit.stakeholder_contract_helpers import field_names

from evidence_corpus.domain.values import SpeakerKind
from stakeholder_model.domain.events import (
    HistoricalPositionRecorded,
    WeakAttributionFlagged,
)
from stakeholder_model.domain.services import CorpusAttributionRule
from stakeholder_model.domain.stakeholder import Stakeholder, StakeholderProfile
from stakeholder_model.domain.values import (
    AttributionStrength,
    BudgetLimit,
    BudgetPeriod,
    HistoricalPosition,
    InstitutionCategory,
    InstitutionIdentity,
    MandateScope,
    MandateSource,
    PassageId,
    PowerSourceKind,
    StakeholderId,
)


def test_attribution_strength_classifies_sources() -> None:
    assert AttributionStrength.EXPLICIT.is_explicit() is True
    assert AttributionStrength.REPORTED.is_explicit() is False
    assert AttributionStrength.MENTION.is_explicit() is False
    assert AttributionStrength.MENTION.is_usable is False
    assert AttributionStrength.EXPLICIT.is_usable is True


def test_position_records_attribution_and_usability() -> None:
    assert field_names(HistoricalPosition) == [
        "id",
        "stance",
        "attribution",
        "stated_on",
        "passage_id",
        "usable",
    ]
    assert hasattr(HistoricalPosition, "new")


def test_recording_returns_a_position() -> None:
    signature = inspect.signature(Stakeholder.record_historical_position)

    assert list(signature.parameters) == [
        "self",
        "stance",
        "attribution",
        "stated_on",
        "passage_id",
    ]


def test_weak_attribution_event_payload_is_frozen() -> None:
    assert WeakAttributionFlagged.name == "WeakAttributionFlagged"
    assert field_names(WeakAttributionFlagged) == [
        "stakeholder_id",
        "passage_id",
        "attribution",
    ]


def _source() -> MandateSource:
    return MandateSource(
        kind=PowerSourceKind.STATUTORY,
        citation="§ 23 ASVG",
        as_of=date(2026, 1, 1),
    )


def _stakeholder() -> Stakeholder:
    return Stakeholder(
        id=StakeholderId("stk_1"),
        identity=InstitutionIdentity(
            name="Österreichische Gesundheitskasse",
            short_name="ÖGK",
            category=InstitutionCategory.PAYER,
            code="oegk",
        ),
        profile=StakeholderProfile(
            mandate_scope=MandateScope(
                topics=frozenset({"waiting_times"}),
                description="Capacity planning",
                source=_source(),
            ),
            budget=BudgetLimit(
                amount_eur=Decimal("100"),
                period=BudgetPeriod.ANNUAL,
                tolerance=0.0,
                source=_source(),
            ),
        ),
    )


def test_mention_only_position_is_unusable_and_flagged() -> None:
    stakeholder = _stakeholder()

    position = stakeholder.record_historical_position(
        stance="supports a waiting-time cap",
        attribution=AttributionStrength.MENTION,
        stated_on=date(2026, 1, 1),
        passage_id=PassageId("psg_1"),
    )

    assert position.usable is False
    assert stakeholder.history == [position]
    assert isinstance(stakeholder.events[0], WeakAttributionFlagged)
    assert isinstance(stakeholder.events[1], HistoricalPositionRecorded)


def test_reported_position_is_also_weak() -> None:
    stakeholder = _stakeholder()

    position = stakeholder.record_historical_position(
        stance="reported to support a cap",
        attribution=AttributionStrength.REPORTED,
        stated_on=date(2026, 1, 1),
        passage_id=PassageId("psg_2"),
    )

    assert position.usable is False
    assert any(isinstance(event, WeakAttributionFlagged) for event in stakeholder.events)


def test_explicit_position_is_usable_and_not_flagged() -> None:
    stakeholder = _stakeholder()

    position = stakeholder.record_historical_position(
        stance="supports a waiting-time cap",
        attribution=AttributionStrength.EXPLICIT,
        stated_on=date(2026, 1, 1),
        passage_id=PassageId("psg_3"),
    )

    assert position.usable is True
    assert isinstance(stakeholder.events[0], HistoricalPositionRecorded)
    assert not any(isinstance(event, WeakAttributionFlagged) for event in stakeholder.events)


def test_position_new_derives_identity_and_usability() -> None:
    position = HistoricalPosition.new(
        stance="mentions the topic",
        attribution=AttributionStrength.MENTION,
        stated_on=date(2026, 1, 1),
        passage_id=PassageId("psg_4"),
    )

    assert position.id.startswith("pos_")
    assert position.usable is False


def test_attribution_rule_reads_corpus_context() -> None:
    rule = CorpusAttributionRule()

    assert rule.classify(SpeakerKind.INSTITUTION, explicitly_named=True) is (
        AttributionStrength.EXPLICIT
    )
    assert rule.classify(SpeakerKind.PERSON, explicitly_named=False) is (
        AttributionStrength.REPORTED
    )
    assert rule.classify(SpeakerKind.ANONYMOUS, explicitly_named=True) is (
        AttributionStrength.MENTION
    )
