"""Unit-of-work adapter for the API-key repository (ADR-002).

Canonical: .pi/architecture/modules/identity-access.md

Each repository call opens the ambient request transaction or its own short-lived session, so the
key store never holds a long-lived ``AsyncSession`` in the composition root.
"""

from __future__ import annotations

from datetime import datetime

from identity_access.infrastructure.repository.records import ApiKeyRecord
from identity_access.infrastructure.repository.sqlalchemy import SqlAlchemyApiKeyRepository
from shared.db import UnitOfWork


class UnitOfWorkApiKeyRepository:
    """Delegate each call to a per-operation SQLAlchemy repository."""

    def __init__(self, unit_of_work: UnitOfWork) -> None:
        self._uow = unit_of_work

    async def add(self, record: ApiKeyRecord) -> None:
        async with self._uow.session() as session:
            await SqlAlchemyApiKeyRepository(session).add(record)

    async def get(self, key_id: str) -> ApiKeyRecord | None:
        async with self._uow.session() as session:
            return await SqlAlchemyApiKeyRepository(session).get(key_id)

    async def find_by_hash(self, key_hash: str) -> ApiKeyRecord | None:
        async with self._uow.session() as session:
            return await SqlAlchemyApiKeyRepository(session).find_by_hash(key_hash)

    async def list(self) -> list[ApiKeyRecord]:
        async with self._uow.session() as session:
            return await SqlAlchemyApiKeyRepository(session).list()

    async def revoke(self, key_id: str, revoked_at: datetime) -> None:
        async with self._uow.session() as session:
            await SqlAlchemyApiKeyRepository(session).revoke(key_id, revoked_at)
