"""Contract freeze: weak attribution may never override an explicit statement."""

from __future__ import annotations

import inspect

from tests.unit.stakeholder_contract_helpers import field_names

from stakeholder_model.domain.services import select_current_position
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
