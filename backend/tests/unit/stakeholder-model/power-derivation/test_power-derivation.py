"""Contract freeze: power is derived, never assigned (ADR-008)."""

from __future__ import annotations

import inspect

from tests.unit.stakeholder_contract_helpers import field_names

from stakeholder_model.domain.stakeholder import Stakeholder
from stakeholder_model.domain.values import NegotiatingPower


def test_negotiating_power_has_component_fields() -> None:
    assert field_names(NegotiatingPower) == [
        "scope",
        "budget",
        "vetoes",
        "centrality",
        "total",
    ]


def test_derive_accepts_only_grounded_inputs() -> None:
    signature = inspect.signature(NegotiatingPower.derive)

    assert list(signature.parameters) == [
        "mandate_scope",
        "budget",
        "veto_rights",
        "dependencies",
    ]
    assert not inspect.iscoroutinefunction(NegotiatingPower.derive)


def test_aggregate_exposes_derivation_not_assignment() -> None:
    assert "negotiating_power" in {
        name for name, value in vars(Stakeholder).items() if callable(value)
    }
    assert not any(name.startswith("set_") and "power" in name for name in dir(Stakeholder))
