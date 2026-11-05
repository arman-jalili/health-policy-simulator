"""Principal resolvers for static/local provisioning and tests (ADR-005).

Canonical: .pi/architecture/modules/identity-access.md

``StaticPrincipalResolver`` maps opaque keys to principals held in memory. It is the adapter for
the local/static demo provisioning path and for contract tests; issue #36 adds the hashed,
database-backed store. Keys are never logged and unknown keys use the same 401 as a missing one.
"""

from __future__ import annotations

from collections.abc import Mapping
from types import MappingProxyType

from identity_access.interfaces.errors import AuthenticationRequiredError
from identity_access.interfaces.types import Principal


class StaticPrincipalResolver:
    """Resolve a presented key from an immutable in-memory mapping."""

    def __init__(self, principals: Mapping[str, Principal]) -> None:
        self._principals = MappingProxyType(dict(principals))

    async def resolve(self, api_key: str | None) -> Principal:
        if not api_key:
            raise AuthenticationRequiredError("Missing X-API-Key header")

        principal = self._principals.get(api_key)
        if principal is None:
            raise AuthenticationRequiredError("Unknown API key")
        return principal
