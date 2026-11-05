"""Scope enforcement: analyst keys are refused corpus writes; operator/admin pass."""

from __future__ import annotations

from collections.abc import AsyncIterator
from types import SimpleNamespace

import httpx
import pytest

from identity_access.infrastructure.resolvers import StaticPrincipalResolver
from identity_access.interfaces.errors import InsufficientScopeError
from identity_access.interfaces.types import ROLE_SCOPES, Principal, Role, Scope
from shared.app import create_app
from shared.config import Settings
from shared.enums import AuthMode, Persistence

DATABASE_URL = "postgresql+asyncpg://hps:hps@localhost:5433/health_policy"

ANALYST = Principal(label="analyst-1", role=Role.ANALYST, scopes=ROLE_SCOPES[Role.ANALYST])
OPERATOR = Principal(label="operator-1", role=Role.OPERATOR, scopes=ROLE_SCOPES[Role.OPERATOR])
ADMIN = Principal(label="admin-1", role=Role.ADMIN, scopes=ROLE_SCOPES[Role.ADMIN])


@pytest.fixture
async def api_client() -> AsyncIterator[httpx.AsyncClient]:
    app = create_app(
        Settings(
            _env_file=None,
            database_url=DATABASE_URL,
            persistence=Persistence.MEMORY,
            auth_mode=AuthMode.STRICT,
        )
    )
    # The static adapter stands in for the hashed key store until issue #36.
    app.state.identity_access = SimpleNamespace(
        principal_port=StaticPrincipalResolver(
            {
                "analyst-key": ANALYST,
                "operator-key": OPERATOR,
                "admin-key": ADMIN,
            }
        )
    )
    transport = httpx.ASGITransport(app=app, raise_app_exceptions=False)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        yield client


def test_analyst_can_write_runs_but_not_the_corpus() -> None:
    assert ANALYST.has_scope(Scope.RUNS_WRITE)
    assert not ANALYST.has_scope(Scope.CORPUS_WRITE)


def test_admin_scope_is_a_wildcard() -> None:
    assert ADMIN.has_scope(Scope.CORPUS_WRITE)
    assert ADMIN.has_scope(Scope.BRIEFS_PUBLISH)


def test_a_missing_scope_is_a_403_with_a_stable_code() -> None:
    error = InsufficientScopeError("missing corpus:write")

    assert error.status_code == 403
    assert error.code == "SCOPE_REQUIRED"


async def test_analyst_key_is_refused_a_corpus_write(api_client: httpx.AsyncClient) -> None:
    response = await api_client.post(
        "/api/v1/corpus/documents",
        json={},
        headers={"X-API-Key": "analyst-key"},
    )

    assert response.status_code == 403, response.text
    body = response.json()
    assert body["code"] == "SCOPE_REQUIRED"
    assert body["details"][0]["code"] == "corpus:write"


async def test_operator_key_passes_the_scope_check(api_client: httpx.AsyncClient) -> None:
    response = await api_client.post(
        "/api/v1/corpus/documents",
        json={},
        headers={"X-API-Key": "operator-key"},
    )

    # The scope check passed; the empty body is rejected by request validation.
    assert response.status_code == 422, response.text


async def test_admin_wildcard_reaches_the_handler(api_client: httpx.AsyncClient) -> None:
    response = await api_client.get(
        "/api/v1/corpus/authority-rules",
        headers={"X-API-Key": "admin-key"},
    )

    assert response.status_code == 200, response.text
    assert isinstance(response.json(), list)
