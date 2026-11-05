"""Database-backed principal resolver (ADR-005).

Canonical: .pi/architecture/modules/identity-access.md

The resolver turns a presented key into the ACL ``Principal``. Missing, unknown and revoked keys all
produce the same 401 contract, so callers cannot use the error to enumerate keys.
"""

from __future__ import annotations

from identity_access.infrastructure.ports import ApiKeyStore
from identity_access.interfaces.errors import AuthenticationRequiredError
from identity_access.interfaces.types import ROLE_SCOPES, Principal


class KeyResolver:
    """Resolve a hashed-store key to a principal, or reject it."""

    def __init__(self, store: ApiKeyStore) -> None:
        self._store = store

    async def resolve(self, api_key: str | None) -> Principal:
        if not api_key:
            raise AuthenticationRequiredError("Missing X-API-Key header")

        record = await self._store.lookup(api_key)
        if record is None or not record.is_active:
            raise AuthenticationRequiredError("Unknown or revoked API key")

        return Principal(
            label=record.label,
            role=record.role,
            scopes=ROLE_SCOPES[record.role],
            is_demo=False,
        )
