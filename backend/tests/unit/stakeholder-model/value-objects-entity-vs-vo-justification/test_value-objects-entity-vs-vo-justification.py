"""Contract freeze: value objects, justified as values not entities (ADR-008)."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any, cast

import pytest
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


def _source() -> values.MandateSource:
    return values.MandateSource(
        kind=values.PowerSourceKind.STATUTORY,
        citation="§ 23 ASVG",
        as_of=date(2026, 1, 1),
    )


def test_value_objects_are_equal_by_state_not_identity() -> None:
    first = values.Interest(topic="waiting_times", goal="Reduce waits", weight=0.8)
    second = values.Interest(topic="waiting_times", goal="Reduce waits", weight=0.8)

    assert first == second
    assert first != values.Interest(topic="waiting_times", goal="Reduce waits", weight=0.5)
    assert hash(first) == hash(second)


def test_identity_and_profile_parts_refuse_blank_values() -> None:
    with pytest.raises(ValueError, match="name"):
        values.InstitutionIdentity(
            name=" ",
            short_name="x",
            category=values.InstitutionCategory.OTHER,
            code="x",
        )
    with pytest.raises(ValueError, match="statement"):
        values.Constraint(statement=" ", topic="benefits")
    with pytest.raises(ValueError, match="topic"):
        values.Interest(topic="", goal="goal", weight=0.5)


def test_mandate_scope_requires_topics_and_covers_them_case_insensitively() -> None:
    with pytest.raises(ValueError, match="topics"):
        values.MandateScope(topics=frozenset(), description="x", source=_source())

    scope = values.MandateScope(
        topics=frozenset({"Waiting Times"}),
        description="Capacity planning",
        source=_source(),
    )

    assert scope.covers("waiting times") is True
    assert scope.covers("benefits") is False


def test_budget_limit_is_bounded_and_honours_tolerance() -> None:
    budget = values.BudgetLimit(
        amount_eur=Decimal("100"),
        period=values.BudgetPeriod.ANNUAL,
        tolerance=0.1,
        source=_source(),
    )

    assert budget.allows(Decimal("110")) is True
    assert budget.allows(Decimal("111")) is False
    with pytest.raises(ValueError, match="non-negative"):
        budget.allows(Decimal("-1"))
    with pytest.raises(ValueError, match="non-negative"):
        values.BudgetLimit(
            amount_eur=Decimal("-1"),
            period=values.BudgetPeriod.ANNUAL,
            tolerance=0.0,
            source=_source(),
        )


def test_dependency_and_priority_guard_their_ranges() -> None:
    with pytest.raises(ValueError, match="different"):
        values.Dependency(
            from_id=values.StakeholderId("stk_1"),
            to_id=values.StakeholderId("stk_1"),
            kind=values.DependencyKind.FUNDING,
            strength=0.5,
        )
    with pytest.raises(ValueError, match="at least 1"):
        values.DecisionPriority(rank=0, topic="waiting_times")
    with pytest.raises(ValueError, match="within"):
        values.NegotiatingPower(scope=1.1, budget=0.0, vetoes=0.0, centrality=0.0, total=0.0)


def test_persona_card_requires_a_code() -> None:
    with pytest.raises(ValueError, match="code"):
        values.PersonaCard(
            code=" ",
            identity=values.InstitutionIdentity(
                name="ÖGK",
                short_name="ÖGK",
                category=values.InstitutionCategory.PAYER,
                code="oegk",
            ),
        )
