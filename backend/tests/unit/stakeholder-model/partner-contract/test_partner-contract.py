"""Contract freeze: the partner contract exposes no repository or ORM types."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from tests.unit.stakeholder_contract_helpers import SRC, field_names, imported_names

from evidence_corpus.domain.values import AuthorityTier
from stakeholder_model.application.dto import StakeholderProfileResult
from stakeholder_model.domain.agent_binding import AgentBinding
from stakeholder_model.domain.stakeholder import StakeholderProfile
from stakeholder_model.domain.values import (
    AttributionStrength,
    BindingId,
    BudgetLimit,
    BudgetPeriod,
    Constraint,
    HistoricalPosition,
    InstitutionCategory,
    InstitutionIdentity,
    Interest,
    MandateScope,
    MandateSource,
    NegotiatingPower,
    PassageId,
    PersonaVersion,
    PositionId,
    PowerSourceKind,
    ProfileVersion,
    ProposalClass,
    RunId,
    StakeholderId,
    VetoRight,
)
from stakeholder_model.interfaces.published import (
    AgentBindingView,
    InstitutionalAllowlistView,
    StakeholderProfileView,
    to_allowlist_view,
    to_binding_view,
    to_profile_view,
)

PUBLISHED = SRC / "interfaces" / "published.py"


def test_profile_view_field_set_is_frozen() -> None:
    assert field_names(StakeholderProfileView) == [
        "stakeholder_id",
        "identity",
        "interests",
        "constraints",
        "budget",
        "mandate_scope",
        "priorities",
        "red_lines",
        "veto_rights",
        "positions",
        "profile_version",
    ]


def test_allowlist_and_binding_views_are_frozen() -> None:
    assert field_names(InstitutionalAllowlistView) == ["institutions"]
    assert field_names(AgentBindingView) == [
        "binding_id",
        "run_id",
        "stakeholder_id",
        "persona_version",
        "allowed_evidence_tiers",
        "red_lines",
    ]


def test_published_module_imports_no_persistence_technology() -> None:
    imports = " ".join(sorted(imported_names(PUBLISHED)))

    assert "sqlalchemy" not in imports
    assert "asyncpg" not in imports
    assert "psycopg" not in imports
    assert "repository" not in imports


def test_partner_contract_mappers_exist() -> None:
    assert callable(to_profile_view)
    assert callable(to_binding_view)
    assert callable(to_allowlist_view)


def _source() -> MandateSource:
    return MandateSource(
        kind=PowerSourceKind.STATUTORY,
        citation="§ 23 ASVG",
        as_of=date(2026, 1, 1),
    )


def _identity() -> InstitutionIdentity:
    return InstitutionIdentity(
        name="Österreichische Gesundheitskasse",
        short_name="ÖGK",
        category=InstitutionCategory.PAYER,
        code="oegk",
    )


def _profile_result() -> StakeholderProfileResult:
    return StakeholderProfileResult(
        stakeholder_id=StakeholderId("stk_oegk"),
        identity=_identity(),
        profile=StakeholderProfile(
            mandate_scope=MandateScope(
                topics=frozenset({"waiting_times", "benefits"}),
                description="Coverage and benefit administration",
                source=_source(),
            ),
            budget=BudgetLimit(
                amount_eur=Decimal("12500000000"),
                period=BudgetPeriod.ANNUAL,
                tolerance=0.02,
                source=_source(),
            ),
            interests=[Interest(topic="waiting_times", goal="Reduce waits", weight=0.9)],
            constraints=[Constraint(statement="No benefit cut", topic="benefits")],
            red_lines=["Abolition of statutory benefits"],
            version=ProfileVersion("2026.1"),
        ),
        veto_rights=(
            VetoRight(
                proposal_class=ProposalClass.STATUTORY_BENEFIT_CHANGE,
                source=_source(),
            ),
        ),
        power=NegotiatingPower(scope=0.5, budget=1.0, vetoes=0.33, centrality=0.0, total=0.5),
        positions=(
            HistoricalPosition(
                id=PositionId("pos_1"),
                stance="supports the cap",
                attribution=AttributionStrength.EXPLICIT,
                stated_on=date(2026, 1, 1),
                passage_id=PassageId("psg_1"),
                usable=True,
            ),
        ),
    )


def test_profile_mapping_publishes_references_and_provenance_only() -> None:
    view = to_profile_view(_profile_result())

    assert view.identity.code == "oegk"
    assert view.mandate_scope.topics == ("benefits", "waiting_times")
    assert view.budget.source_citation == "§ 23 ASVG"
    assert view.veto_rights[0].proposal_class is ProposalClass.STATUTORY_BENEFIT_CHANGE
    assert view.positions[0].passage_id == "psg_1"
    assert view.profile_version == "2026.1"
    assert not hasattr(view, "passage_text")
    assert not hasattr(view, "session")
    assert not hasattr(view, "orm_row")


def test_binding_and_allowlist_mapping() -> None:
    binding = AgentBinding(
        id=BindingId("bnd_1"),
        run_id=RunId("run_1"),
        stakeholder_id=StakeholderId("stk_oegk"),
        persona_version=PersonaVersion("2026.1"),
        allowed_evidence_tiers=frozenset({AuthorityTier.LEGISLATION}),
        red_lines=("No benefit cut",),
    )

    binding_view = to_binding_view(binding)
    allowlist = to_allowlist_view([_identity()])

    assert binding_view.allowed_evidence_tiers == (AuthorityTier.LEGISLATION,)
    assert binding_view.red_lines == ("No benefit cut",)
    assert allowlist.institutions[0].code == "oegk"
