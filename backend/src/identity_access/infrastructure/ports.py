"""Infrastructure-internal ports: key material and the store adapter.

Canonical: .pi/architecture/modules/identity-access.md

``KeyMaterial`` and ``ApiKeyRecord`` are key-store types. Nothing outside this package may import
them (ACL isolation, acceptance criterion 6).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable

from identity_access.infrastructure.repository.records import ApiKeyRecord
from identity_access.interfaces.ports import ApiKeyAdminPort


@dataclass(frozen=True, slots=True)
class KeyMaterial:
    """Generated key material; only the plaintext is returned to the caller, exactly once."""

    key_id: str
    plaintext_key: str = field(repr=False)
    key_hash: str = field(repr=False)
    salt: str = field(repr=False)


@runtime_checkable
class ApiKeyFactory(Protocol):
    """Generate high-entropy key material and its salted hash."""

    def generate(self) -> KeyMaterial:
        """Return a fresh key id, plaintext key, hash and salt."""
        ...


@runtime_checkable
class ApiKeyStore(ApiKeyAdminPort, Protocol):
    """Infrastructure adapter implementing the admin port plus credential lookup."""

    async def lookup(self, api_key: str) -> ApiKeyRecord | None:
        """Find the active record for a presented plaintext key, or ``None``."""
        ...
