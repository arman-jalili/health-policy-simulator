"""Alembic environment: async engine, settings-driven URL, shared metadata.

Run from the repository root: ``alembic upgrade head``. ``DATABASE_URL`` must be set
(``.env`` is honoured), so a misconfigured environment fails here rather than at runtime.
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

from alembic import context
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import create_async_engine

# ``src/`` layout: make the shared kernel importable without installing the package.
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from shared import audit, outbox  # noqa: F401  (imports register tables on Base.metadata)
from shared.config import get_settings
from shared.db import Base

config = context.config
target_metadata = Base.metadata


def _database_url() -> str:
    return str(get_settings().database_url)


def run_migrations_offline() -> None:
    """Emit SQL to stdout without connecting."""
    url = _database_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def _run_migrations(connection: Connection) -> None:
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
        compare_server_default=True,
    )
    with context.begin_transaction():
        context.run_migrations()


async def _run_async_migrations() -> None:
    engine = create_async_engine(_database_url(), poolclass=pool.NullPool)
    try:
        async with engine.connect() as connection:
            await connection.run_sync(_run_migrations)
    finally:
        await engine.dispose()


def run_migrations_online() -> None:
    """Apply migrations against DATABASE_URL."""
    asyncio.run(_run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
