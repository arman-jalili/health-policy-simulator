"""Concrete resolution outcomes for the IdentityAccess request pipeline (ADR-008).

Canonical: .pi/architecture/modules/identity-access.md

Resolution is a request outcome, not an aggregate: these factories return immutable value objects
and never persist anything. They give the resolver, the scope guard and the revocation check one
place to express the state diagram; consumers decide the HTTP status from the final state.
"""

from __future__ import annotations

from identity_access.interfaces.dto import ResolutionOutcome
from identity_access.interfaces.types import Principal, ResolutionState, Scope


def anonymous() -> ResolutionOutcome:
    """No credential was presented and strict mode rejected the request."""
    return ResolutionOutcome(state=ResolutionState.ANONYMOUS)


def resolved(principal: Principal) -> ResolutionOutcome:
    """A credential resolved to an actor; the scope check has not run yet."""
    return ResolutionOutcome(state=ResolutionState.RESOLVED, principal=principal)


def authorized(principal: Principal) -> ResolutionOutcome:
    """The resolved principal carries the scope required by the route."""
    return ResolutionOutcome(state=ResolutionState.AUTHORIZED, principal=principal)


def forbidden(principal: Principal, required_scope: Scope) -> ResolutionOutcome:
    """The principal resolved, but it lacks the scope the route declares."""
    return ResolutionOutcome(
        state=ResolutionState.FORBIDDEN,
        principal=principal,
        reason=f"missing scope: {required_scope.value}",
    )


def revoked(reason: str = "key revoked") -> ResolutionOutcome:
    """The presented key was revoked; callers must respond 401 immediately."""
    if not reason.strip():
        raise ValueError("revocation reason must be non-empty")
    return ResolutionOutcome(state=ResolutionState.REVOKED, reason=reason)


def rejected(reason: str) -> ResolutionOutcome:
    """The credential was missing, malformed or unknown."""
    if not reason.strip():
        raise ValueError("rejection reason must be non-empty")
    return ResolutionOutcome(state=ResolutionState.REJECTED, reason=reason)
