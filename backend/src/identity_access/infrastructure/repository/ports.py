"""Persistence port for the API-key store (migration 0104).

Canonical: .pi/architecture/modules/identity-access.md

The table shape is hidden here. The application-facing contract is ``ApiKeyAdminPort``; this port
is internal to the infrastructure adapter.
"""

from __future__ import annotations

from datetime import datetime
from typing import Protocol, runtime_checkable

from identity_access.infrastructure.repository.records import ApiKeyRecord


@runtime_checkable
class ApiKeyRepository(Protocol):
    """Store and look up hashed API keys; never persists plaintext."""

    async def add(self, record: ApiKeyRecord) -> None: ...

    async def get(self, key_id: str) -> ApiKeyRecord | None: ...

    async def find_by_hash(self, key_hash: str) -> ApiKeyRecord | None: ...

    async def list(self) -> list[ApiKeyRecord]: ...

    async def revoke(self, key_id: str, revoked_at: datetime) -> None: ...
