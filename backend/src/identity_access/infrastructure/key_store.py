"""Hash-backed API-key store (ADR-005).

Canonical: .pi/architecture/modules/identity-access.md

Implements the public ``ApiKeyAdminPort`` plus the credential lookup used by the resolver. The
plaintext key is returned exactly once from ``create_key`` and never logged or stored.
"""

from __future__ import annotations

import hmac
from collections.abc import Sequence
from datetime import UTC, datetime

from identity_access.infrastructure.keys import hash_key
from identity_access.infrastructure.ports import ApiKeyFactory
from identity_access.infrastructure.repository.ports import ApiKeyRepository
from identity_access.infrastructure.repository.records import ApiKeyRecord
from identity_access.interfaces.dto import ApiKeySummary, CreateApiKeyCommand, IssuedApiKey
from identity_access.interfaces.errors import ApiKeyNotFoundError


class HashedApiKeyStore:
    """Issue, list, revoke and look up salted-hash API keys."""

    def __init__(self, repository: ApiKeyRepository, factory: ApiKeyFactory) -> None:
        self._repository = repository
        self._factory = factory

    async def create_key(self, command: CreateApiKeyCommand) -> IssuedApiKey:
        material = self._factory.generate()
        created_at = datetime.now(UTC)
        await self._repository.add(
            ApiKeyRecord(
                key_id=material.key_id,
                label=command.label,
                role=command.role,
                key_hash=material.key_hash,
                salt=material.salt,
                created_at=created_at,
            )
        )
        return IssuedApiKey(
            key_id=material.key_id,
            key=material.plaintext_key,
            label=command.label,
            role=command.role,
            created_at=created_at,
        )

    async def list_keys(self) -> Sequence[ApiKeySummary]:
        return [
            ApiKeySummary(
                key_id=record.key_id,
                label=record.label,
                role=record.role,
                created_at=record.created_at,
                revoked_at=record.revoked_at,
            )
            for record in await self._repository.list()
        ]

    async def revoke_key(self, key_id: str) -> None:
        record = await self._repository.get(key_id)
        if record is None:
            raise ApiKeyNotFoundError(f"No API key with id {key_id!r}")
        if record.is_active:
            await self._repository.revoke(key_id, datetime.now(UTC))

    async def lookup(self, api_key: str) -> ApiKeyRecord | None:
        key_id, separator, secret = api_key.partition(".")
        if not separator or not key_id or not secret:
            return None
        record = await self._repository.get(key_id)
        if record is None or not record.is_active:
            return None
        if not hmac.compare_digest(hash_key(secret, record.salt), record.key_hash):
            return None
        return record
