"""Contract freeze: institutions-only identity and the person-representation error."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest
from tests.unit.stakeholder_contract_helpers import field_names

from shared.errors import AppError
from stakeholder_model.domain.errors import PersonRepresentationForbidden
from stakeholder_model.domain.stakeholder import Stakeholder, StakeholderProfile
from stakeholder_model.domain.values import (
    BudgetLimit,
    BudgetPeriod,
    InstitutionCategory,
    InstitutionIdentity,
    MandateScope,
    MandateSource,
    PowerSourceKind,
    StakeholderId,
)


def test_person_representation_error_is_frozen() -> None:
    assert issubclass(PersonRepresentationForbidden, AppError)
    assert PersonRepresentationForbidden.code == "PERSON_REPRESENTATION_FORBIDDEN"
    assert PersonRepresentationForbidden.status_code == 422


def test_identity_exposes_the_person_flag() -> None:
    identity = InstitutionIdentity(
        name="Dr. Maria Huber",
        short_name="Huber",
        category=InstitutionCategory.PROVIDER,
        code="person-1",
        is_natural_person=True,
    )

    assert identity.is_person is True
    assert isinstance(identity, InstitutionIdentity)


def test_institutional_identity_is_grounded_in_a_mandate_source() -> None:
    source = MandateSource(
        kind=PowerSourceKind.STATUTORY,
        citation="§ 23 ASVG",
        as_of=date(2026, 1, 1),
    )

    assert source.citation == "§ 23 ASVG"
    assert field_names(MandateSource) == ["kind", "citation", "as_of"]


def test_stakeholder_declares_the_identity_guard_location() -> None:
    assert "identity" in field_names(Stakeholder)
    assert hasattr(Stakeholder, "__post_init__")


def _identity(**overrides: object) -> InstitutionIdentity:
    payload: dict[str, object] = {
        "name": "Österreichische Gesundheitskasse",
        "short_name": "ÖGK",
        "category": InstitutionCategory.PAYER,
        "code": "oegk",
    }
    payload.update(overrides)
    return InstitutionIdentity(**payload)  # type: ignore[arg-type]


def _stakeholder(identity: InstitutionIdentity) -> Stakeholder:
    return Stakeholder(
        id=StakeholderId("stk_1"),
        identity=identity,
        profile=StakeholderProfile(
            mandate_scope=MandateScope(
                topics=frozenset({"waiting_times"}),
                description="Capacity planning",
                source=MandateSource(
                    kind=PowerSourceKind.STATUTORY,
                    citation="§ 23 ASVG",
                    as_of=date(2026, 1, 1),
                ),
            ),
            budget=BudgetLimit(
                amount_eur=Decimal("100"),
                period=BudgetPeriod.ANNUAL,
                tolerance=0.0,
                source=MandateSource(
                    kind=PowerSourceKind.STATUTORY,
                    citation="§ 23 ASVG",
                    as_of=date(2026, 1, 1),
                ),
            ),
        ),
    )


def test_declared_natural_person_cannot_be_a_stakeholder() -> None:
    with pytest.raises(PersonRepresentationForbidden, match="natural person"):
        _stakeholder(_identity(name="Dr. Maria Huber", is_natural_person=True))


def test_honorific_is_refused_even_when_flag_is_false() -> None:
    with pytest.raises(PersonRepresentationForbidden):
        _stakeholder(_identity(name="Prof. Karl Weber", is_natural_person=False))


def test_institutional_identity_is_accepted() -> None:
    stakeholder = _stakeholder(_identity())

    assert stakeholder.identity.is_person is False
