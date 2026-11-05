"""Frozen identity types and the ACL value object (ADR-005, ADR-008).

Canonical: .pi/architecture/modules/identity-access.md

These names are the published language of the context. Handlers pass a :class:`Principal` around;
key-store records never cross this boundary.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum
from types import MappingProxyType
from typing import Final, NewType


class Role(StrEnum):
    """Named scope bundle assigned to an API key."""

    ANALYST = "analyst"
    OPERATOR = "operator"
    ADMIN = "admin"


class Scope(StrEnum):
    """Permission token checked at the route boundary (ADR-005)."""

    RUNS_READ = "runs:read"
    RUNS_WRITE = "runs:write"
    CORPUS_READ = "corpus:read"
    CORPUS_WRITE = "corpus:write"
    BRIEFS_READ = "briefs:read"
    BRIEFS_PUBLISH = "briefs:publish"
    ADMIN = "admin"


ROLE_SCOPES: Final[Mapping[Role, frozenset[Scope]]] = MappingProxyType(
    {
        Role.ANALYST: frozenset({Scope.RUNS_READ, Scope.RUNS_WRITE, Scope.BRIEFS_READ}),
        Role.OPERATOR: frozenset(
            {
                Scope.RUNS_READ,
                Scope.RUNS_WRITE,
                Scope.BRIEFS_READ,
                Scope.CORPUS_READ,
                Scope.CORPUS_WRITE,
                Scope.BRIEFS_PUBLISH,
            }
        ),
        # Wildcard: Principal.has_scope treats ADMIN as satisfying every scope.
        Role.ADMIN: frozenset({Scope.ADMIN}),
    }
)


class ResolutionState(StrEnum):
    """Request outcome of credential resolution; deliberately not an aggregate (ADR-008)."""

    ANONYMOUS = "anonymous"
    RESOLVED = "resolved"
    AUTHORIZED = "authorized"
    FORBIDDEN = "forbidden"
    REVOKED = "revoked"
    REJECTED = "rejected"


ActorId = NewType("ActorId", str)
"""Stable attribution label recorded on every command event and metered invocation."""


@dataclass(frozen=True, slots=True)
class Principal:
    """Resolved actor; the only published concept of this context (ADR-005)."""

    label: str
    role: Role
    scopes: frozenset[Scope]
    is_demo: bool = False

    def __post_init__(self) -> None:
        if not self.label.strip():
            raise ValueError("Principal.label must be non-empty for attribution")

    def has_scope(self, required: Scope) -> bool:
        """Return whether this principal may perform ``required`` (ADMIN is a wildcard)."""
        return Scope.ADMIN in self.scopes or required in self.scopes

    def actor_id(self) -> ActorId:
        """Translate the ACL label to the attribution value handlers pass downstream."""
        return ActorId(self.label)
