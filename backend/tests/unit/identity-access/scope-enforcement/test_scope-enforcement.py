"""Contract freeze: scopes are declared per role and enforced at the route boundary."""

from __future__ import annotations

from identity_access.interfaces.errors import InsufficientScopeError
from identity_access.interfaces.types import ROLE_SCOPES, Principal, Role, Scope


def test_analyst_can_write_runs_but_not_the_corpus() -> None:
    analyst = Principal(label="analyst-1", role=Role.ANALYST, scopes=ROLE_SCOPES[Role.ANALYST])

    assert analyst.has_scope(Scope.RUNS_WRITE)
    assert not analyst.has_scope(Scope.CORPUS_WRITE)


def test_admin_scope_is_a_wildcard() -> None:
    admin = Principal(label="root", role=Role.ADMIN, scopes=ROLE_SCOPES[Role.ADMIN])

    assert admin.has_scope(Scope.CORPUS_WRITE)
    assert admin.has_scope(Scope.BRIEFS_PUBLISH)


def test_a_missing_scope_is_a_403_with_a_stable_code() -> None:
    error = InsufficientScopeError("missing corpus:write")

    assert error.status_code == 403
    assert error.code == "SCOPE_REQUIRED"
