"""Wiring: the guard router is mounted and boot fails closed on an empty allowlist."""

from __future__ import annotations

import pytest

from governance_compliance.application.errors import AllowlistEmpty
from governance_compliance.application.values import AllowlistEntry, InstitutionalAllowlist
from governance_compliance.composition import build_container
from governance_compliance.infrastructure.allowlist import StaticAllowlistSource
from shared.app import create_app
from shared.config import Settings
from shared.enums import Persistence

TEST_URL = "postgresql+asyncpg://hps:hps@localhost:5433/health_policy"
POPULATED = InstitutionalAllowlist(
    institutions=(
        AllowlistEntry(
            code="bmsgpk",
            canonical_name="BMSGPK",
            short_name="BMSGPK",
            category="ministry",
        ),
    )
)


def test_app_mounts_the_governance_routes() -> None:
    app = create_app(
        Settings(_env_file=None, database_url=TEST_URL, persistence=Persistence.MEMORY)
    )
    paths = set(app.openapi()["paths"])
    assert "/api/v1/governance/check" in paths
    assert "/api/v1/governance/violations" in paths
    assert "/api/v1/positions/{position_id}/provenance" in paths
    assert "/api/v1/governance/allowlist" in paths


def test_empty_allowlist_aborts_boot() -> None:
    with pytest.raises(AllowlistEmpty):
        build_container(
            Settings(_env_file=None, database_url=TEST_URL, persistence=Persistence.MEMORY),
            allowlist_source=StaticAllowlistSource(InstitutionalAllowlist()),
        )


def test_populated_allowlist_builds_a_guard_without_an_llm_client() -> None:
    container = build_container(
        Settings(_env_file=None, database_url=TEST_URL, persistence=Persistence.MEMORY),
        allowlist_source=StaticAllowlistSource(POPULATED),
    )
    assert container.allowlist.is_empty is False
    assert container.enforce_institution_only_output is not None
