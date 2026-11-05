"""Shared test fixtures: hermetic settings, deterministic clock, ASGI client."""

from __future__ import annotations

from collections.abc import AsyncIterator
from datetime import UTC, datetime
from typing import Any, cast

import httpx
import pytest
from fastapi import FastAPI

from shared.app import create_app
from shared.clock import FixedClock
from shared.config import Settings
from shared.enums import Persistence

TEST_DATABASE_URL = "postgresql+asyncpg://hps:hps@localhost:5433/health_policy"
FIXED_MOMENT = datetime(2026, 11, 5, 9, 30, tzinfo=UTC)

_ENV_VARS = (
    "ENV",
    "AUTH_MODE",
    "DATABASE_URL",
    "DB_ECHO",
    "DB_POOL_SIZE",
    "DB_MAX_OVERFLOW",
    "DB_CONNECT_TIMEOUT_S",
    "PERSISTENCE",
    "LOG_LEVEL",
    "LOG_FORMAT",
    "CORS_ORIGINS",
    "API_HOST",
    "API_PORT",
)


@pytest.fixture(autouse=True)
def isolated_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    """Keep the developer's shell and ``.env`` from leaking into tests."""
    for name in _ENV_VARS:
        monkeypatch.delenv(name, raising=False)


@pytest.fixture
def settings() -> Settings:
    return Settings(
        _env_file=None,
        database_url=TEST_DATABASE_URL,
        persistence=Persistence.MEMORY,
    )


class StubDatabase:
    """Stand-in for :class:`shared.db.Database` that never opens a connection."""

    def __init__(self, error: Exception | None = None) -> None:
        self.error = error
        self.ping_count = 0

    async def ping(self) -> None:
        self.ping_count += 1
        if self.error is not None:
            raise self.error


@pytest.fixture
def app(settings: Settings) -> FastAPI:
    return create_app(settings)


@pytest.fixture
def stub_database(app: FastAPI) -> StubDatabase:
    stub = StubDatabase()
    app.state.db = stub
    return stub


@pytest.fixture
def failing_database(app: FastAPI) -> StubDatabase:
    stub = StubDatabase(error=OSError("connection refused"))
    app.state.db = stub
    return stub


@pytest.fixture
async def client(app: FastAPI) -> AsyncIterator[httpx.AsyncClient]:
    transport = httpx.ASGITransport(app=app, raise_app_exceptions=False)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as http_client:
        yield http_client


@pytest.fixture
def fixed_clock() -> FixedClock:
    return FixedClock(FIXED_MOMENT)


def as_async_session(session: Any) -> Any:
    """Cast a lightweight fake to the session protocol used by writers."""
    return cast(Any, session)
