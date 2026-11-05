"""Contract freeze: profile completeness before activation."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from tests.unit.stakeholder_contract_helpers import field_names

from shared.errors import AppError
from stakeholder_model.domain.errors import IncompleteProfile
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


def _source() -> MandateSource:
    return MandateSource(
        kind=PowerSourceKind.STATUTORY,
        citation="§ 23 ASVG",
        as_of=date(2026, 1, 1),
    )


def test_incomplete_profile_error_is_frozen() -> None:
    assert issubclass(IncompleteProfile, AppError)
    assert IncompleteProfile.code == "INCOMPLETE_PROFILE"
    assert IncompleteProfile.status_code == 422


def test_profile_can_represent_the_incomplete_state() -> None:
    profile = StakeholderProfile(
        mandate_scope=MandateScope(
            topics=frozenset({"waiting_times"}),
            description="Planning and funding of care capacity",
            source=_source(),
        ),
        budget=BudgetLimit(
            amount_eur=Decimal("0"),
            period=BudgetPeriod.ANNUAL,
            tolerance=0.0,
            source=_source(),
        ),
    )

    assert profile.interests == []
    assert profile.constraints == []
    assert callable(profile.is_complete)


def test_activation_is_the_guard_boundary() -> None:
    assert "activate" in {name for name, value in vars(Stakeholder).items() if callable(value)}
    assert field_names(StakeholderProfile) == [
        "mandate_scope",
        "budget",
        "interests",
        "constraints",
        "priorities",
        "red_lines",
        "version",
    ]
    assert StakeholderId("stk_1") == "stk_1"
    assert (
        InstitutionIdentity(
            name="ÖGK",
            short_name="ÖGK",
            category=InstitutionCategory.PAYER,
            code="oegk",
        ).code
        == "oegk"
    )
