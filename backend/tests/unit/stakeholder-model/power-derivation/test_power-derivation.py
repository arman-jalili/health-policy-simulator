"""Contract freeze: power is derived, never assigned (ADR-008)."""

from __future__ import annotations

import inspect
from datetime import date
from decimal import Decimal

import pytest
from tests.unit.stakeholder_contract_helpers import field_names

from stakeholder_model.domain.stakeholder import Stakeholder, StakeholderProfile
from stakeholder_model.domain.values import (
    BudgetLimit,
    BudgetPeriod,
    Dependency,
    DependencyKind,
    InstitutionCategory,
    InstitutionIdentity,
    MandateScope,
    MandateSource,
    NegotiatingPower,
    PowerSourceKind,
    ProposalClass,
    StakeholderId,
    VetoRight,
)


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


def _source() -> MandateSource:
    return MandateSource(
        kind=PowerSourceKind.STATUTORY,
        citation="§ 23 ASVG",
        as_of=date(2026, 1, 1),
    )


def _scope(*topics: str) -> MandateScope:
    return MandateScope(
        topics=frozenset(topics or ("waiting_times",)),
        description="Capacity planning",
        source=_source(),
    )


def _budget(amount: str = "100000000") -> BudgetLimit:
    return BudgetLimit(
        amount_eur=Decimal(amount),
        period=BudgetPeriod.ANNUAL,
        tolerance=0.0,
        source=_source(),
    )


def _veto() -> VetoRight:
    return VetoRight(proposal_class=ProposalClass.STATUTORY_BENEFIT_CHANGE, source=_source())


def test_identical_inputs_derive_identical_power() -> None:
    first = NegotiatingPower.derive(
        mandate_scope=_scope("waiting_times", "benefits"),
        budget=_budget(),
        veto_rights=[_veto()],
        dependencies=[],
    )
    second = NegotiatingPower.derive(
        mandate_scope=_scope("waiting_times", "benefits"),
        budget=_budget(),
        veto_rights=[_veto()],
        dependencies=[],
    )

    assert first == second
    assert first.total == pytest.approx(0.5 * 0.30 + 0.25 + 0.30 / 3)


def test_each_driver_is_bounded_and_monotonic() -> None:
    base = NegotiatingPower.derive(
        mandate_scope=_scope(),
        budget=_budget("0"),
        veto_rights=[],
        dependencies=[],
    )
    richer = NegotiatingPower.derive(
        mandate_scope=_scope("a", "b", "c", "d", "e"),
        budget=_budget("1000000000000"),
        veto_rights=[_veto(), _veto(), _veto(), _veto()],
        dependencies=[],
    )

    assert 0.0 <= base.total <= 1.0
    assert 0.0 <= richer.total <= 1.0
    assert richer.scope == 1.0
    assert richer.budget == 1.0
    assert richer.vetoes == 1.0
    assert richer.total > base.total


def test_more_vetoes_raise_only_the_veto_component() -> None:
    one = NegotiatingPower.derive(
        mandate_scope=_scope(), budget=_budget(), veto_rights=[_veto()], dependencies=[]
    )
    two = NegotiatingPower.derive(
        mandate_scope=_scope(), budget=_budget(), veto_rights=[_veto(), _veto()], dependencies=[]
    )

    assert one.scope == two.scope
    assert one.budget == two.budget
    assert one.centrality == two.centrality
    assert two.vetoes > one.vetoes
    assert two.total > one.total


def test_dependencies_drive_centrality() -> None:
    dependency = Dependency(
        from_id=StakeholderId("stk_1"),
        to_id=StakeholderId("stk_2"),
        kind=DependencyKind.FUNDING,
        strength=0.8,
    )

    without = NegotiatingPower.derive(
        mandate_scope=_scope(), budget=_budget(), veto_rights=[], dependencies=[]
    )
    with_dependency = NegotiatingPower.derive(
        mandate_scope=_scope(),
        budget=_budget(),
        veto_rights=[],
        dependencies=[dependency],
    )

    assert without.centrality == 0.0
    assert with_dependency.centrality == 0.25
    assert with_dependency.total > without.total


def test_stakeholder_delegates_to_the_derivation() -> None:
    stakeholder = Stakeholder(
        id=StakeholderId("stk_1"),
        identity=InstitutionIdentity(
            name="Österreichische Gesundheitskasse",
            short_name="ÖGK",
            category=InstitutionCategory.PAYER,
            code="oegk",
        ),
        profile=StakeholderProfile(
            mandate_scope=_scope(),
            budget=_budget(),
        ),
        veto_rights=[_veto()],
    )

    assert stakeholder.negotiating_power() == NegotiatingPower.derive(
        mandate_scope=stakeholder.profile.mandate_scope,
        budget=stakeholder.profile.budget,
        veto_rights=stakeholder.veto_rights,
        dependencies=stakeholder.dependencies,
    )
