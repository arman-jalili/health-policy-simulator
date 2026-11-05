"""Contract freeze: persona cards are validated configuration loaded at boot."""

from __future__ import annotations

from tests.unit.stakeholder_contract_helpers import field_names, method_names

from stakeholder_model.application.dto import PersonaCardResult
from stakeholder_model.application.ports import PersonaLoaderPort
from stakeholder_model.domain.values import PersonaCard
from stakeholder_model.infrastructure.personas import PersonaFactory
from stakeholder_model.interfaces.published import InstitutionView


def test_persona_card_is_validated_configuration_not_aggregate_state() -> None:
    assert field_names(PersonaCard) == [
        "code",
        "identity",
        "interests",
        "constraints",
        "red_lines",
        "version",
    ]
    assert field_names(PersonaCardResult) == [
        "code",
        "identity",
        "interest_count",
        "constraint_count",
        "persona_version",
    ]


def test_persona_loader_is_a_factory_port() -> None:
    assert method_names(PersonaLoaderPort) == {"load_all", "load"}
    assert method_names(PersonaFactory) == {"load_all", "load"}


def test_persona_identity_is_institutional_only() -> None:
    assert field_names(InstitutionView) == ["name", "short_name", "category", "code"]
    assert "is_natural_person" not in field_names(InstitutionView)
