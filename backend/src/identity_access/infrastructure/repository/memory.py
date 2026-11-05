"""In-memory API-key repository for tests and ``PERSISTENCE=memory`` (ADR-002).

Canonical: .pi/architecture/modules/identity-access.md
"""

from __future__ import annotations

from dataclasses import replace
from datetime import datetime

from identity_access.infrastructure.repository.records import ApiKeyRecord


class InMemoryApiKeyRepository:
    """Store hashed key records in a process-local mapping."""

    def __init__(self) -> None:
        self._records: dict[str, ApiKeyRecord] = {}

    async def add(self, record: ApiKeyRecord) -> None:
        self._records[record.key_id] = record

    async def get(self, key_id: str) -> ApiKeyRecord | None:
        return self._records.get(key_id)

    async def find_by_hash(self, key_hash: str) -> ApiKeyRecord | None:
        return next(
            (record for record in self._records.values() if record.key_hash == key_hash),
            None,
        )

    async def list(self) -> list[ApiKeyRecord]:
        return list(self._records.values())

    async def revoke(self, key_id: str, revoked_at: datetime) -> None:
        record = self._records.get(key_id)
        if record is not None:
            self._records[key_id] = replace(record, revoked_at=revoked_at)
