"""Contract freeze: persona cards are validated configuration loaded at boot."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml
from tests.unit.stakeholder_contract_helpers import field_names, method_names

from stakeholder_model.application.dto import PersonaCardResult
from stakeholder_model.application.ports import PersonaLoaderPort
from stakeholder_model.domain.errors import PersonRepresentationForbidden
from stakeholder_model.domain.values import InstitutionCategory, PersonaCard
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


PERSONA_DIRECTORY = Path("config/personas")


def test_all_nine_personas_load_and_are_complete() -> None:
    stakeholders = PersonaFactory(PERSONA_DIRECTORY).load_all()

    assert len(stakeholders) == 9
    assert {stakeholder.identity.code for stakeholder in stakeholders} == {
        "aerztekammer",
        "apothekerkammer",
        "bmsgpk",
        "krankenhausgesellschaft",
        "landesgesundheitsfonds",
        "oegk",
        "patientenanwaltschaft",
        "privatkrankenanstalten",
        "sozialversicherung",
    }
    for stakeholder in stakeholders:
        assert stakeholder.profile.interests, stakeholder.identity.code
        assert stakeholder.profile.constraints, stakeholder.identity.code
        assert stakeholder.identity.is_person is False
        stakeholder.activate()


def test_load_one_persona_by_code() -> None:
    oegk = PersonaFactory(PERSONA_DIRECTORY).load("oegk")

    assert oegk.identity.name == "Österreichische Gesundheitskasse"
    assert oegk.identity.category is InstitutionCategory.PAYER
    assert oegk.profile.mandate_scope.covers("waiting_times")


def test_persona_without_interests_aborts_the_load(tmp_path: Path) -> None:
    document = yaml.safe_load((PERSONA_DIRECTORY / "oegk.yaml").read_text(encoding="utf-8"))
    document["code"] = "empty"
    document["interests"] = []
    (tmp_path / "empty.yaml").write_text(
        yaml.safe_dump(document, allow_unicode=True, sort_keys=False), encoding="utf-8"
    )

    with pytest.raises(ValueError, match="no interests"):
        PersonaFactory(tmp_path).load_all()


def test_personal_name_aborts_the_load(tmp_path: Path) -> None:
    document = yaml.safe_load((PERSONA_DIRECTORY / "oegk.yaml").read_text(encoding="utf-8"))
    document["code"] = "personal"
    document["identity"]["name"] = "Dr. Maria Huber"
    (tmp_path / "personal.yaml").write_text(
        yaml.safe_dump(document, allow_unicode=True, sort_keys=False), encoding="utf-8"
    )

    with pytest.raises(PersonRepresentationForbidden):
        PersonaFactory(tmp_path).load_all()
