"""Contract freeze: authority must cite a MandateSource and refusals are events."""

from __future__ import annotations

import inspect
from datetime import date
from decimal import Decimal

import pytest
from tests.unit.stakeholder_contract_helpers import field_names

from shared.errors import AppError
from stakeholder_model.domain.errors import UnsourcedAuthority
from stakeholder_model.domain.events import AuthorityClaimRejected, MandateSourceCited
from stakeholder_model.domain.stakeholder import Stakeholder, StakeholderProfile
from stakeholder_model.domain.values import (
    BudgetLimit,
    BudgetPeriod,
    InstitutionCategory,
    InstitutionIdentity,
    MandateScope,
    MandateSource,
    PowerSourceKind,
    ProposalClass,
    StakeholderId,
    VetoRight,
)


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


def _source(kind: PowerSourceKind = PowerSourceKind.STATUTORY) -> MandateSource:
    return MandateSource(kind=kind, citation="§ 23 ASVG", as_of=date(2026, 1, 1))


def _stakeholder() -> Stakeholder:
    return Stakeholder(
        id=StakeholderId("stk_1"),
        identity=InstitutionIdentity(
            name="Österreichische Gesundheitskasse",
            short_name="ÖGK",
            category=InstitutionCategory.PAYER,
            code="oegk",
        ),
        profile=StakeholderProfile(
            mandate_scope=MandateScope(
                topics=frozenset({"waiting_times"}),
                description="Capacity planning",
                source=_source(),
            ),
            budget=BudgetLimit(
                amount_eur=Decimal("100"),
                period=BudgetPeriod.ANNUAL,
                tolerance=0.0,
                source=_source(),
            ),
        ),
    )


def test_unspecified_source_is_rejected_and_emits_event() -> None:
    stakeholder = _stakeholder()
    veto = VetoRight(proposal_class=ProposalClass.STATUTORY_BENEFIT_CHANGE, source=_source())

    with pytest.raises(UnsourcedAuthority) as caught:
        stakeholder.cite_power_source(veto, _source(PowerSourceKind.UNSPECIFIED))

    assert caught.value.power_type == "VetoRight"
    assert isinstance(stakeholder.events[0], AuthorityClaimRejected)


def test_missing_source_is_rejected() -> None:
    stakeholder = _stakeholder()
    scope = MandateScope(
        topics=frozenset({"waiting_times"}),
        description="Capacity planning",
        source=_source(),
    )

    with pytest.raises(UnsourcedAuthority):
        stakeholder.cite_power_source(scope, None)

    rejected = stakeholder.events[0]
    assert isinstance(rejected, AuthorityClaimRejected)
    assert rejected.power_type == "MandateScope"


def test_sourced_claim_emits_citation_without_rejection() -> None:
    stakeholder = _stakeholder()
    budget = BudgetLimit(
        amount_eur=Decimal("100"),
        period=BudgetPeriod.ANNUAL,
        tolerance=0.0,
        source=_source(),
    )

    stakeholder.cite_power_source(budget, _source())

    assert len(stakeholder.events) == 1
    cited = stakeholder.events[0]
    assert isinstance(cited, MandateSourceCited)
    assert cited.power_type == "BudgetLimit"
    assert cited.citation == "§ 23 ASVG"


def test_rejection_event_survives_the_raise() -> None:
    stakeholder = _stakeholder()
    veto = VetoRight(proposal_class=ProposalClass.STATUTORY_BENEFIT_CHANGE, source=_source())

    with pytest.raises(UnsourcedAuthority):
        stakeholder.cite_power_source(veto, _source(PowerSourceKind.UNSPECIFIED))

    assert len(stakeholder.drain_events()) == 1
    assert stakeholder.events == []
