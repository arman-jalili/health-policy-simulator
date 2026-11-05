"""SQLAlchemy adapter for the API-key repository (ADR-002).

Canonical: .pi/architecture/modules/identity-access.md

The repository hides the table shape; callers only see ``ApiKeyRecord``. It never stores or returns
plaintext key material.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from identity_access.infrastructure.repository.models import ApiKeyRow
from identity_access.infrastructure.repository.records import ApiKeyRecord
from identity_access.interfaces.types import Role


def _to_record(row: ApiKeyRow) -> ApiKeyRecord:
    return ApiKeyRecord(
        key_id=row.key_id,
        label=row.label,
        role=Role(row.role),
        key_hash=row.key_hash,
        salt=row.salt,
        created_at=row.created_at,
        revoked_at=row.revoked_at,
    )


class SqlAlchemyApiKeyRepository:
    """Persist and query hashed API keys."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, record: ApiKeyRecord) -> None:
        self._session.add(
            ApiKeyRow(
                key_id=record.key_id,
                label=record.label,
                role=record.role.value,
                key_hash=record.key_hash,
                salt=record.salt,
                created_at=record.created_at,
                revoked_at=record.revoked_at,
            )
        )
        await self._session.flush()

    async def get(self, key_id: str) -> ApiKeyRecord | None:
        row = await self._session.get(ApiKeyRow, key_id)
        return _to_record(row) if row is not None else None

    async def find_by_hash(self, key_hash: str) -> ApiKeyRecord | None:
        row = await self._session.scalar(select(ApiKeyRow).where(ApiKeyRow.key_hash == key_hash))
        return _to_record(row) if row is not None else None

    async def list(self) -> list[ApiKeyRecord]:
        rows = await self._session.scalars(select(ApiKeyRow).order_by(ApiKeyRow.created_at))
        return [_to_record(row) for row in rows]

    async def revoke(self, key_id: str, revoked_at: datetime) -> None:
        row = await self._session.get(ApiKeyRow, key_id)
        if row is not None:
            row.revoked_at = revoked_at
            await self._session.flush()
