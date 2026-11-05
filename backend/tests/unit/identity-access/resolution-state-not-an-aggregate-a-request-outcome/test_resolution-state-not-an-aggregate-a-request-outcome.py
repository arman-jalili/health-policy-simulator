"""ResolutionState is a request outcome, not an aggregate (ADR-008)."""

from __future__ import annotations

import pytest

from identity_access.interfaces.dto import ResolutionOutcome
from identity_access.interfaces.resolution import (
    anonymous,
    authorized,
    forbidden,
    rejected,
    resolved,
    revoked,
)
from identity_access.interfaces.types import Principal, ResolutionState, Role, Scope


def test_resolution_state_covers_every_request_outcome() -> None:
    assert {state.value for state in ResolutionState} == {
        "anonymous",
        "resolved",
        "authorized",
        "forbidden",
        "revoked",
        "rejected",
    }


def test_resolution_outcome_carries_state_and_an_optional_principal() -> None:
    principal = Principal(label="analyst-1", role=Role.ANALYST, scopes=frozenset({Scope.RUNS_READ}))
    outcome = ResolutionOutcome(state=ResolutionState.AUTHORIZED, principal=principal)

    assert outcome.state is ResolutionState.AUTHORIZED
    assert outcome.principal == principal
    assert outcome.reason is None


def test_anonymous_is_terminal_and_has_no_principal() -> None:
    outcome = anonymous()

    assert outcome.state is ResolutionState.ANONYMOUS
    assert outcome.principal is None
    assert outcome.reason is None


def test_resolved_keeps_the_principal_before_the_scope_check() -> None:
    principal = Principal(label="analyst-1", role=Role.ANALYST, scopes=frozenset({Scope.RUNS_READ}))
    outcome = resolved(principal)

    assert outcome.state is ResolutionState.RESOLVED
    assert outcome.principal == principal


def test_authorized_preserves_the_principal() -> None:
    principal = Principal(label="analyst-1", role=Role.ANALYST, scopes=frozenset({Scope.RUNS_READ}))
    outcome = authorized(principal)

    assert outcome.state is ResolutionState.AUTHORIZED
    assert outcome.principal == principal


def test_forbidden_names_the_scope_that_was_missing() -> None:
    principal = Principal(label="analyst-1", role=Role.ANALYST, scopes=frozenset({Scope.RUNS_READ}))
    outcome = forbidden(principal, Scope.CORPUS_WRITE)

    assert outcome.state is ResolutionState.FORBIDDEN
    assert outcome.principal == principal
    assert outcome.reason == "missing scope: corpus:write"


def test_revoked_and_rejected_require_a_reason() -> None:
    with pytest.raises(ValueError, match="reason"):
        revoked("   ")

    with pytest.raises(ValueError, match="reason"):
        rejected("")
