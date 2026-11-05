"""Demo guard: local-only principals and a hard refusal in production (ADR-005)."""

from __future__ import annotations

import httpx
import pytest
from pydantic import ValidationError

from identity_access.infrastructure.demo import LoopbackDemoPolicy
from identity_access.interfaces.demo import is_loopback_host
from identity_access.interfaces.ports import DemoModePolicy
from shared.app import create_app
from shared.config import Settings
from shared.enums import AuthMode, Environment, Persistence

DATABASE_URL = "postgresql+asyncpg://hps:hps@localhost:5433/health_policy"


def _settings(*, auth_mode: AuthMode = AuthMode.DEMO) -> Settings:
    return Settings(
        _env_file=None,
        database_url=DATABASE_URL,
        env=Environment.LOCAL,
        auth_mode=auth_mode,
        persistence=Persistence.MEMORY,
    )


def test_demo_mode_is_refused_in_production() -> None:
    with pytest.raises(ValidationError, match="AUTH_MODE=demo"):
        Settings(
            _env_file=None,
            database_url=DATABASE_URL,
            env=Environment.PRODUCTION,
            auth_mode=AuthMode.DEMO,
            persistence=Persistence.MEMORY,
        )


def test_demo_policy_is_a_port_with_a_localhost_predicate() -> None:
    assert hasattr(DemoModePolicy, "permits")


def test_only_loopback_hosts_are_recognised() -> None:
    for loopback in ("127.0.0.1", "127.1.2.3", "::1", "localhost", "testclient"):
        assert is_loopback_host(loopback) is True, loopback

    for non_loopback in ("203.0.113.5", "example.com", "", None):
        assert is_loopback_host(non_loopback) is False, non_loopback


def test_loopback_policy_uses_the_same_predicate() -> None:
    policy = LoopbackDemoPolicy()

    assert policy.permits("127.0.0.1") is True
    assert policy.permits("203.0.113.5") is False


async def test_demo_mode_allows_a_loopback_client(client: httpx.AsyncClient) -> None:
    response = await client.post("/api/v1/corpus/documents", json={})

    assert response.status_code != 401


async def test_demo_mode_rejects_a_non_loopback_client() -> None:
    app = create_app(_settings())
    transport = httpx.ASGITransport(
        app=app,
        raise_app_exceptions=False,
        client=("203.0.113.5", 12345),
    )
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.post("/api/v1/corpus/documents", json={})

    assert response.status_code == 401, response.text
    assert response.json()["code"] == "UNAUTHENTICATED"
