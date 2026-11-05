"""Contract freeze: authority must cite a MandateSource and refusals are events."""

from __future__ import annotations

import inspect

from tests.unit.stakeholder_contract_helpers import field_names

from shared.errors import AppError
from stakeholder_model.domain.errors import UnsourcedAuthority
from stakeholder_model.domain.events import AuthorityClaimRejected
from stakeholder_model.domain.stakeholder import Stakeholder
from stakeholder_model.domain.values import MandateSource, PowerSourceKind, VetoRight


def test_unsourced_authority_error_is_frozen() -> None:
    assert issubclass(UnsourcedAuthority, AppError)
    assert UnsourcedAuthority.code == "UNSOURCED_AUTHORITY"
    assert UnsourcedAuthority.status_code == 422


def test_unspecified_source_is_representable_but_not_admissible() -> None:
    assert PowerSourceKind.UNSPECIFIED.value == "unspecified"
    assert field_names(MandateSource) == ["kind", "citation", "as_of"]
    assert field_names(VetoRight) == ["proposal_class", "source"]


def test_cite_power_source_has_a_frozen_signature() -> None:
    signature = inspect.signature(Stakeholder.cite_power_source)

    assert list(signature.parameters) == ["self", "power", "source"]


def test_authority_rejection_event_payload_is_frozen() -> None:
    assert AuthorityClaimRejected.__module__ == "stakeholder_model.domain.events"
    assert AuthorityClaimRejected.name == "AuthorityClaimRejected"
    assert field_names(AuthorityClaimRejected) == ["stakeholder_id", "power_type", "reason"]
