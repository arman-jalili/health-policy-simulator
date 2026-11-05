"""Contract freeze: aggregate roots and their command surface (ADR-008)."""

from __future__ import annotations

import dataclasses
import inspect
from datetime import date
from decimal import Decimal

import pytest
from tests.unit.stakeholder_contract_helpers import field_names, method_names

from stakeholder_model.domain.agent_binding import AgentBinding
from stakeholder_model.domain.errors import (
    IncompleteProfile,
    PersonRepresentationForbidden,
    UnsourcedAuthority,
)
from stakeholder_model.domain.events import AuthorityClaimRejected, MandateSourceCited
from stakeholder_model.domain.stakeholder import Stakeholder, StakeholderProfile
from stakeholder_model.domain.values import (
    BudgetLimit,
    BudgetPeriod,
    Constraint,
    InstitutionCategory,
    InstitutionIdentity,
    Interest,
    MandateScope,
    MandateSource,
    PowerSourceKind,
    ProposalClass,
    StakeholderId,
    VetoRight,
)


def test_stakeholder_is_the_aggregate_root() -> None:
    assert Stakeholder.__module__ == "stakeholder_model.domain.stakeholder"
    assert field_names(Stakeholder) == [
        "id",
        "identity",
        "profile",
        "veto_rights",
        "dependencies",
        "history",
        "events",
    ]
    assert dataclasses.is_dataclass(Stakeholder)


def test_stakeholder_owns_the_command_surface() -> None:
    methods = method_names(Stakeholder)

    assert {
        "register_interest",
        "declare_constraint",
        "activate",
        "cite_power_source",
        "record_historical_position",
        "negotiating_power",
        "drain_events",
    } <= methods
    assert not inspect.iscoroutinefunction(Stakeholder.cite_power_source)


def test_profile_is_part_of_the_stakeholder_aggregate() -> None:
    assert StakeholderProfile.__module__ == "stakeholder_model.domain.stakeholder"
    assert field_names(StakeholderProfile) == [
        "mandate_scope",
        "budget",
        "interests",
        "constraints",
        "priorities",
        "red_lines",
        "version",
    ]
    assert {"is_complete", "add_interest", "declare_constraint"} <= method_names(StakeholderProfile)


def test_agent_binding_is_a_separate_aggregate_root() -> None:
    assert AgentBinding.__module__ == "stakeholder_model.domain.agent_binding"
    assert field_names(AgentBinding) == [
        "id",
        "run_id",
        "stakeholder_id",
        "persona_version",
        "allowed_evidence_tiers",
        "red_lines",
    ]
    assert "assert_institution_only" in method_names(AgentBinding)


def _source(kind: PowerSourceKind = PowerSourceKind.STATUTORY) -> MandateSource:
    return MandateSource(kind=kind, citation="§ 23 ASVG", as_of=date(2026, 1, 1))


def _profile(
    *,
    interests: list[Interest] | None = None,
    constraints: list[Constraint] | None = None,
) -> StakeholderProfile:
    return StakeholderProfile(
        mandate_scope=MandateScope(
            topics=frozenset({"waiting_times"}),
            description="Planning and funding of care capacity",
            source=_source(),
        ),
        budget=BudgetLimit(
            amount_eur=Decimal("1000000"),
            period=BudgetPeriod.ANNUAL,
            tolerance=0.05,
            source=_source(),
        ),
        interests=list(interests or []),
        constraints=list(constraints or []),
    )


def _stakeholder(
    *,
    identity: InstitutionIdentity | None = None,
    profile: StakeholderProfile | None = None,
) -> Stakeholder:
    return Stakeholder(
        id=StakeholderId("stk_1"),
        identity=identity
        or InstitutionIdentity(
            name="Österreichische Gesundheitskasse",
            short_name="ÖGK",
            category=InstitutionCategory.PAYER,
            code="oegk",
        ),
        profile=profile or _profile(),
    )


def test_constructing_a_personal_stakeholder_is_refused() -> None:
    with pytest.raises(PersonRepresentationForbidden, match="natural person"):
        _stakeholder(
            identity=InstitutionIdentity(
                name="Dr. Maria Huber",
                short_name="Huber",
                category=InstitutionCategory.PROVIDER,
                code="person-1",
                is_natural_person=True,
            )
        )


def test_honorific_name_is_refused_even_without_the_flag() -> None:
    with pytest.raises(PersonRepresentationForbidden):
        _stakeholder(
            identity=InstitutionIdentity(
                name="Mag. Anna Berger",
                short_name="Berger",
                category=InstitutionCategory.PROVIDER,
                code="person-2",
            )
        )


def test_activation_refuses_a_profile_without_interests() -> None:
    stakeholder = _stakeholder(
        profile=_profile(constraints=[Constraint(statement="No benefit cut", topic="benefits")])
    )

    with pytest.raises(IncompleteProfile) as caught:
        stakeholder.activate()

    assert caught.value.missing == ("interests",)


def test_activation_refuses_a_profile_without_constraints() -> None:
    stakeholder = _stakeholder(
        profile=_profile(
            interests=[Interest(topic="waiting_times", goal="Reduce waits", weight=1.0)]
        )
    )

    with pytest.raises(IncompleteProfile) as caught:
        stakeholder.activate()

    assert caught.value.missing == ("constraints",)


def test_activation_accepts_a_complete_profile() -> None:
    stakeholder = _stakeholder(
        profile=_profile(
            interests=[Interest(topic="waiting_times", goal="Reduce waits", weight=1.0)],
            constraints=[Constraint(statement="No benefit cut", topic="benefits")],
        )
    )

    stakeholder.activate()
    assert stakeholder.profile.is_complete()


def test_registering_interest_and_constraint_completes_the_profile() -> None:
    stakeholder = _stakeholder()

    stakeholder.register_interest(Interest(topic="waiting_times", goal="Reduce waits", weight=0.8))
    stakeholder.declare_constraint(Constraint(statement="No benefit cut", topic="benefits"))
    stakeholder.activate()

    assert stakeholder.profile.is_complete()


def test_unsourced_authority_is_refused_and_emits_an_event() -> None:
    stakeholder = _stakeholder()
    veto = VetoRight(proposal_class=ProposalClass.STATUTORY_BENEFIT_CHANGE, source=_source())

    with pytest.raises(UnsourcedAuthority):
        stakeholder.cite_power_source(veto, _source(PowerSourceKind.UNSPECIFIED))

    assert len(stakeholder.events) == 1
    rejected = stakeholder.events[0]
    assert isinstance(rejected, AuthorityClaimRejected)
    assert rejected.stakeholder_id == "stk_1"
    assert rejected.power_type == "VetoRight"


def test_missing_source_is_treated_as_unsourced_authority() -> None:
    stakeholder = _stakeholder()
    veto = VetoRight(proposal_class=ProposalClass.STATUTORY_BENEFIT_CHANGE, source=_source())

    with pytest.raises(UnsourcedAuthority):
        stakeholder.cite_power_source(veto, None)

    assert isinstance(stakeholder.events[0], AuthorityClaimRejected)


def test_sourced_authority_emits_mandate_source_cited() -> None:
    stakeholder = _stakeholder()
    veto = VetoRight(proposal_class=ProposalClass.STATUTORY_BENEFIT_CHANGE, source=_source())

    stakeholder.cite_power_source(veto, _source())

    assert len(stakeholder.events) == 1
    cited = stakeholder.events[0]
    assert isinstance(cited, MandateSourceCited)
    assert cited.citation == "§ 23 ASVG"


def test_drain_events_returns_and_clears() -> None:
    stakeholder = _stakeholder()
    veto = VetoRight(proposal_class=ProposalClass.STATUTORY_BENEFIT_CHANGE, source=_source())
    stakeholder.cite_power_source(veto, _source())

    drained = stakeholder.drain_events()

    assert len(drained) == 1
    assert stakeholder.events == []
