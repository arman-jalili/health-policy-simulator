"""Contract freeze: value objects, justified as values not entities (ADR-008)."""

from __future__ import annotations

from typing import Any, cast

from tests.unit.stakeholder_contract_helpers import enum_values, field_names

from stakeholder_model.domain import values

VALUE_OBJECTS = (
    values.InstitutionIdentity,
    values.Interest,
    values.Constraint,
    values.BudgetLimit,
    values.DecisionPriority,
    values.MandateScope,
    values.MandateSource,
    values.VetoRight,
    values.Dependency,
    values.NegotiatingPower,
    values.HistoricalPosition,
    values.MaterialityScore,
)


def test_every_value_object_is_frozen() -> None:
    for value_object in VALUE_OBJECTS:
        assert cast(Any, value_object).__dataclass_params__.frozen is True


def test_identity_fields_are_frozen() -> None:
    assert field_names(values.InstitutionIdentity) == [
        "name",
        "short_name",
        "category",
        "code",
        "is_natural_person",
    ]
    assert isinstance(values.InstitutionIdentity.is_person, property)


def test_value_object_field_sets_are_frozen() -> None:
    assert field_names(values.Interest) == ["topic", "goal", "weight"]
    assert field_names(values.Constraint) == ["statement", "topic"]
    assert field_names(values.BudgetLimit) == ["amount_eur", "period", "tolerance", "source"]
    assert field_names(values.DecisionPriority) == ["rank", "topic"]
    assert field_names(values.MandateScope) == ["topics", "description", "source"]
    assert field_names(values.MandateSource) == ["kind", "citation", "as_of"]
    assert field_names(values.VetoRight) == ["proposal_class", "source"]
    assert field_names(values.Dependency) == ["from_id", "to_id", "kind", "strength"]
    assert field_names(values.NegotiatingPower) == [
        "scope",
        "budget",
        "vetoes",
        "centrality",
        "total",
    ]
    assert field_names(values.HistoricalPosition) == [
        "id",
        "stance",
        "attribution",
        "stated_on",
        "passage_id",
        "usable",
    ]


def test_identifier_newtypes_are_strings() -> None:
    for identifier in (
        values.StakeholderId,
        values.BindingId,
        values.PositionId,
        values.RunId,
        values.ProfileVersion,
        values.PersonaVersion,
        values.PassageId,
    ):
        assert cast(Any, identifier).__supertype__ is str


def test_enums_expose_the_frozen_vocabulary() -> None:
    assert enum_values(values.AttributionStrength) == {"explicit", "reported", "mention"}
    assert "statutory" in enum_values(values.PowerSourceKind)
    assert "unspecified" in enum_values(values.PowerSourceKind)
    assert "statutory_benefit_change" in enum_values(values.ProposalClass)
    assert "payer" in enum_values(values.InstitutionCategory)
