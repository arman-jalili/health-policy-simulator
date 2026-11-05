"""Contract freeze: weak attribution may never override an explicit statement."""

from __future__ import annotations

import inspect
from datetime import date

from tests.unit.stakeholder_contract_helpers import field_names

from stakeholder_model.domain.services import select_current_position
from stakeholder_model.domain.values import (
    AttributionStrength,
    HistoricalPosition,
    PassageId,
    PositionId,
)
from stakeholder_model.interfaces.published import StakeholderProfileView


def test_persona_assembly_has_a_frozen_selection_rule() -> None:
    signature = inspect.signature(select_current_position)

    assert list(signature.parameters) == ["history"]
    assert not inspect.iscoroutinefunction(select_current_position)


def test_partner_contract_publishes_positions_not_raw_history() -> None:
    fields = field_names(StakeholderProfileView)

    assert "positions" in fields
    assert "history" not in fields
    assert "interests" in fields
    assert "constraints" in fields
    assert "red_lines" in fields
    assert "profile_version" in fields


def _position(
    position_id: str,
    *,
    attribution: AttributionStrength,
    stated_on: date,
    stance: str,
) -> HistoricalPosition:
    return HistoricalPosition(
        id=PositionId(position_id),
        stance=stance,
        attribution=attribution,
        stated_on=stated_on,
        passage_id=PassageId(f"psg_{position_id}"),
        usable=attribution.is_usable,
    )


def test_weak_position_never_overrides_an_explicit_statement() -> None:
    explicit = _position(
        "pos_1",
        attribution=AttributionStrength.EXPLICIT,
        stated_on=date(2026, 1, 1),
        stance="supports the cap",
    )
    weak = _position(
        "pos_2",
        attribution=AttributionStrength.MENTION,
        stated_on=date(2026, 6, 1),
        stance="opposes the cap",
    )

    assert select_current_position([explicit, weak]) is explicit
    assert select_current_position([weak, explicit]) is explicit


def test_most_recent_explicit_statement_wins() -> None:
    older = _position(
        "pos_1",
        attribution=AttributionStrength.EXPLICIT,
        stated_on=date(2026, 1, 1),
        stance="supports the cap",
    )
    newer = _position(
        "pos_2",
        attribution=AttributionStrength.EXPLICIT,
        stated_on=date(2026, 3, 1),
        stance="opposes the cap",
    )

    assert select_current_position([newer, older]) is newer


def test_only_weak_history_has_no_current_position() -> None:
    weak = _position(
        "pos_1",
        attribution=AttributionStrength.MENTION,
        stated_on=date(2026, 1, 1),
        stance="mentions the topic",
    )

    assert select_current_position([weak]) is None
    assert select_current_position([]) is None
