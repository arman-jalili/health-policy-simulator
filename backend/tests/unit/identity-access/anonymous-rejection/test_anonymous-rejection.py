"""Anonymous rejection: strict mode never defaults to anonymous (ADR-005)."""

from __future__ import annotations

import inspect
from collections.abc import AsyncIterator

import httpx
import pytest

from identity_access.interfaces.errors import AuthenticationRequiredError
from identity_access.interfaces.ports import PrincipalPort
from shared.app import create_app
from shared.config import Settings
from shared.enums import AuthMode, Persistence

DATABASE_URL = "postgresql+asyncpg://hps:hps@localhost:5433/health_policy"

MUTATING_ROUTES = (
    "/api/v1/corpus/documents",
    "/api/v1/corpus/ingestion-runs",
    "/api/v1/corpus/snapshots",
)

READ_ROUTES = (
    "/api/v1/documents/doc_missing",
    "/api/v1/passages/psg_missing",
    "/api/v1/corpus/authority-rules",
)


@pytest.fixture
async def strict_client() -> AsyncIterator[httpx.AsyncClient]:
    app = create_app(
        Settings(
            _env_file=None,
            database_url=DATABASE_URL,
            persistence=Persistence.MEMORY,
            auth_mode=AuthMode.STRICT,
        )
    )
    transport = httpx.ASGITransport(app=app, raise_app_exceptions=False)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        yield client


async def test_authentication_required_is_a_401_with_a_stable_code() -> None:
    error = AuthenticationRequiredError()

    assert error.status_code == 401
    assert error.code == "UNAUTHENTICATED"
    assert error.envelope("req_contract").code == "UNAUTHENTICATED"


def test_principal_port_declares_resolve_api_key() -> None:
    signature = inspect.signature(PrincipalPort.resolve)

    assert list(signature.parameters) == ["self", "api_key"]


@pytest.mark.parametrize("path", MUTATING_ROUTES)
async def test_every_mutating_corpus_route_rejects_a_missing_key(
    strict_client: httpx.AsyncClient, path: str
) -> None:
    response = await strict_client.post(path, json={})

    assert response.status_code == 401, response.text
    body = response.json()
    assert body["code"] == "UNAUTHENTICATED"
    assert "X-API-Key" in body["message"]


@pytest.mark.parametrize("path", MUTATING_ROUTES)
async def test_an_unknown_key_is_rejected_until_the_store_exists(
    strict_client: httpx.AsyncClient, path: str
) -> None:
    response = await strict_client.post(path, json={}, headers={"X-API-Key": "bogus"})

    assert response.status_code == 401, response.text
    assert response.json()["code"] == "UNAUTHENTICATED"


@pytest.mark.parametrize("path", READ_ROUTES)
async def test_read_routes_also_require_a_key_in_strict_mode(
    strict_client: httpx.AsyncClient, path: str
) -> None:
    response = await strict_client.get(path)

    assert response.status_code == 401, response.text


async def test_health_liveness_stays_auth_free(strict_client: httpx.AsyncClient) -> None:
    response = await strict_client.get("/healthz")

    assert response.status_code == 200


async def test_demo_mode_does_not_require_a_key(client: httpx.AsyncClient) -> None:
    response = await client.post("/api/v1/corpus/documents", json={})

    assert response.status_code != 401
