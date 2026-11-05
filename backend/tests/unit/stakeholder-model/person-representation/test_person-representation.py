"""Contract freeze: institutions-only identity and the person-representation error."""

from __future__ import annotations

from datetime import date

from tests.unit.stakeholder_contract_helpers import field_names

from shared.errors import AppError
from stakeholder_model.domain.errors import PersonRepresentationForbidden
from stakeholder_model.domain.stakeholder import Stakeholder
from stakeholder_model.domain.values import (
    InstitutionCategory,
    InstitutionIdentity,
    MandateSource,
    PowerSourceKind,
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
