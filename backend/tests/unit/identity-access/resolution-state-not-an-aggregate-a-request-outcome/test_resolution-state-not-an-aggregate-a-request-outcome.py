"""Contract freeze: ResolutionState is a request outcome, not an aggregate (ADR-008)."""

from __future__ import annotations

from identity_access.interfaces.dto import ResolutionOutcome
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
