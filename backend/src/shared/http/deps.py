"""Request-scoped dependencies exposed to interface layers."""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import cast

from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession

from shared.config import Settings
from shared.db import Database


def get_app_settings(request: Request) -> Settings:
    """Return the settings the application was built with."""
    return cast(Settings, request.app.state.settings)


def get_database(request: Request) -> Database:
    """Return the process-wide database handle."""
    return cast(Database, request.app.state.db)


def get_trace_id(request: Request) -> str:
    """Return the trace id bound by :class:`RequestContextMiddleware`."""
    return cast(str, getattr(request.state, "trace_id", ""))


async def get_session(request: Request) -> AsyncIterator[AsyncSession]:
    """Yield a transactional session; commit on success, roll back on failure."""
    database = get_database(request)
    async with database.session() as session:
        yield session
