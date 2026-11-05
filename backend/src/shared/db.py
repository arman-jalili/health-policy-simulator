"""Database engine, session factory and declarative base (ADR-002).

One PostgreSQL database, SQLAlchemy 2.x async with asyncpg. Transactions are owned by
application services; this module only hands out sessions and checks connectivity.

Canonical: .pi/architecture/decisions/ADR-002-data-storage-strategy.md
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from contextvars import ContextVar

from sqlalchemy import MetaData, text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from shared.config import Settings

NAMING_CONVENTION = {
    "ix": "ix_%(table_name)s_%(column_0_N_name)s",
    "uq": "uq_%(table_name)s_%(column_0_N_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    """Declarative base for every table owned by any context."""

    metadata = MetaData(naming_convention=NAMING_CONVENTION)


class UnitOfWork:
    """One logical transaction per request (or per explicit script scope).

    Repositories and the outbox publisher share the ambient session so an aggregate write and the
    events it drained commit together. Outside an explicit ``transaction()`` scope each operation
    runs in its own short-lived transaction — that keeps background workers usable without
    pretending they are atomic with the caller.
    """

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory
        self._current: ContextVar[AsyncSession | None] = ContextVar(
            f"unit_of_work:{id(self)}", default=None
        )

    @property
    def has_active_transaction(self) -> bool:
        return self._current.get() is not None

    @asynccontextmanager
    async def transaction(self) -> AsyncIterator[AsyncSession]:
        """Join the ambient transaction or open one; commit on success, roll back on failure."""
        ambient = self._current.get()
        if ambient is not None:
            yield ambient
            return

        async with self._session_factory() as session:
            token = self._current.set(session)
            try:
                yield session
                await session.commit()
            except BaseException:
                await session.rollback()
                raise
            finally:
                self._current.reset(token)

    @asynccontextmanager
    async def session(self) -> AsyncIterator[AsyncSession]:
        """Session to use right now: the ambient one, or a self-committing scope."""
        ambient = self._current.get()
        if ambient is not None:
            yield ambient
            return

        async with self._session_factory() as session:
            try:
                yield session
                await session.commit()
            except BaseException:
                await session.rollback()
                raise


class Database:
    """Owns the async engine and session factory for the process lifetime."""

    def __init__(self, settings: Settings) -> None:
        self._engine: AsyncEngine = create_async_engine(
            str(settings.database_url),
            echo=settings.db_echo,
            pool_size=settings.db_pool_size,
            max_overflow=settings.db_max_overflow,
            pool_pre_ping=True,
            connect_args={
                "timeout": settings.db_connect_timeout_s,
                "server_settings": {"application_name": settings.service_name},
            },
        )
        self._session_factory: async_sessionmaker[AsyncSession] = async_sessionmaker(
            self._engine,
            expire_on_commit=False,
            autoflush=False,
        )

    @property
    def engine(self) -> AsyncEngine:
        return self._engine

    @property
    def session_factory(self) -> async_sessionmaker[AsyncSession]:
        return self._session_factory

    @asynccontextmanager
    async def session(self) -> AsyncIterator[AsyncSession]:
        """Transactional session scope: commit on success, roll back on failure."""
        async with self._session_factory() as session:
            try:
                yield session
                await session.commit()
            except BaseException:
                await session.rollback()
                raise

    async def ping(self) -> None:
        """Raise when the database cannot answer a trivial query."""
        async with self._engine.connect() as connection:
            await connection.execute(text("SELECT 1"))

    async def dispose(self) -> None:
        await self._engine.dispose()
