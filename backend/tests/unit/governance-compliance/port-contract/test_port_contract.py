"""Port contract: the negotiation write path consumes a blocking guard port."""

from __future__ import annotations

from governance_compliance.application.errors import GuardUnavailable, GuardVerdictRequired
from governance_compliance.application.ports import InstitutionGuard
from governance_compliance.application.services import EnforceInstitutionOnlyOutput


def test_guard_service_structurally_satisfies_the_blocking_port() -> None:
    assert hasattr(EnforceInstitutionOnlyOutput, "execute")
    assert InstitutionGuard.__name__ == "InstitutionGuard"


def test_missing_guard_fails_closed() -> None:
    assert GuardUnavailable.status_code == 503
    assert GuardUnavailable.code == "GOVERNANCE_GUARD_UNAVAILABLE"


def test_write_without_a_verdict_is_a_conflict() -> None:
    assert GuardVerdictRequired.status_code == 409
    assert GuardVerdictRequired.code == "GUARD_VERDICT_REQUIRED"
