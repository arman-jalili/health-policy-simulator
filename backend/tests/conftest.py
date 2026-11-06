"""Shared test fixtures: hermetic settings, deterministic clock, ASGI client."""

from __future__ import annotations

import asyncio
import os
from collections.abc import AsyncIterator
from datetime import UTC, datetime
from typing import Any, cast

import asyncpg  # type: ignore[import-untyped]
import httpx
import pytest
from fastapi import FastAPI

from shared.app import create_app
from shared.clock import FixedClock
from shared.config import Settings
from shared.enums import Persistence

_DEFAULT_DATABASE_URL = "postgresql+asyncpg://hps:hps@localhost:5433/health_policy"


def _test_database_url(source: str) -> str:
    """Derive ``<database>_test`` while preserving host, port, credentials and query."""
    prefix = "postgresql+asyncpg://"
    if not source.startswith(prefix):
        raise RuntimeError("DATABASE_URL must use postgresql+asyncpg:// for integration tests")
    from urllib.parse import urlsplit, urlunsplit

    parts = urlsplit(source)
    database = parts.path.lstrip("/") or "health_policy"
    return urlunsplit(
        (parts.scheme, parts.netloc, f"/{database}_test", parts.query, parts.fragment)
    )


_source_url = os.environ.get("DATABASE_URL") or _DEFAULT_DATABASE_URL
_explicit_test_url = os.environ.get("TEST_DATABASE_URL")
TEST_DATABASE_URL = _explicit_test_url or _test_database_url(_source_url)
if (os.environ.get("DATABASE_URL") or os.environ.get("TEST_DATABASE_URL")) is not None:
    os.environ["DATABASE_URL"] = TEST_DATABASE_URL
    os.environ["HPS_TEST_DATABASE_URL"] = TEST_DATABASE_URL


def _is_test_database(url: str) -> bool:
    from urllib.parse import urlsplit

    return urlsplit(url).path.rstrip("/").endswith("_test")


def _admin_url(url: str) -> str:
    from urllib.parse import urlsplit, urlunsplit

    parts = urlsplit(url)
    return urlunsplit((parts.scheme, parts.netloc, "/postgres", parts.query, parts.fragment))


async def _ensure_test_database() -> None:
    test_url = TEST_DATABASE_URL
    if not _is_test_database(test_url):
        if os.environ.get("ALLOW_DESTRUCTIVE_TESTS") == "1":
            return
        raise RuntimeError(
            f"refusing destructive integration tests against non-test database {test_url!r}; "
            "set TEST_DATABASE_URL to a name ending in _test or ALLOW_DESTRUCTIVE_TESTS=1"
        )
    admin = _admin_url(test_url)
    plain = admin.replace("postgresql+asyncpg://", "postgresql://")
    connection = await asyncpg.connect(plain)
    try:
        database = test_url.rsplit("/", 1)[-1].split("?", 1)[0]
        exists = await connection.fetchval("select 1 from pg_database where datname = $1", database)
        if not exists:
            await connection.execute(f'CREATE DATABASE "{database}"')
    finally:
        await connection.close()


@pytest.fixture(scope="session", autouse=True)
def isolated_test_database() -> None:
    """Keep destructive migration fixtures away from the demo database (#421)."""
    if os.environ.get("DATABASE_URL") or os.environ.get("TEST_DATABASE_URL"):
        asyncio.run(_ensure_test_database())


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
