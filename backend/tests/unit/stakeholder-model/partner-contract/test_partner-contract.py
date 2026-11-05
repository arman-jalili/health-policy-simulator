"""Contract freeze: the partner contract exposes no repository or ORM types."""

from __future__ import annotations

from tests.unit.stakeholder_contract_helpers import SRC, field_names, imported_names

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
