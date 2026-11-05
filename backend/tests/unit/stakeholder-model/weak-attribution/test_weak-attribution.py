"""Contract freeze: attribution strength governs position usability."""

from __future__ import annotations

import inspect

from tests.unit.stakeholder_contract_helpers import field_names

from stakeholder_model.domain.events import WeakAttributionFlagged
from stakeholder_model.domain.stakeholder import Stakeholder
from stakeholder_model.domain.values import AttributionStrength, HistoricalPosition


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
