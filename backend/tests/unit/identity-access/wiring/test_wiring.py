"""Wiring: the composition root builds IdentityAccess and every API route is scoped."""

from __future__ import annotations

import asyncio
import re
from dataclasses import fields
from types import SimpleNamespace

import httpx
import pytest
from fastapi import FastAPI

from identity_access.composition import (
    IdentityAccessContainer,
    build_identity_access_container,
)
from identity_access.infrastructure.demo import LoopbackDemoPolicy
from identity_access.infrastructure.key_resolver import KeyResolver
from identity_access.infrastructure.key_store import HashedApiKeyStore
from identity_access.infrastructure.readiness import AlwaysReadyReadiness, DatabaseReadiness
from identity_access.infrastructure.resolvers import StaticPrincipalResolver
from identity_access.interfaces.http.router import router as admin_router
from identity_access.interfaces.types import Principal, Role
from shared.app import create_app
from shared.config import Settings
from shared.db import Database
from shared.enums import AuthMode, Persistence

DATABASE_URL = "postgresql+asyncpg://hps:hps@localhost:5433/health_policy"
HTTP_METHODS = {"get", "post", "put", "patch", "delete"}


def _settings(
    persistence: Persistence = Persistence.MEMORY,
    auth_mode: AuthMode = AuthMode.DEMO,
) -> Settings:
    return Settings(
        _env_file=None,
        database_url=DATABASE_URL,
        persistence=persistence,
        auth_mode=auth_mode,
    )


def test_container_freezes_the_four_wired_ports() -> None:
    assert [field.name for field in fields(IdentityAccessContainer)] == [
        "principal_port",
        "api_key_admin",
        "readiness",
        "demo_policy",
    ]


def test_memory_container_binds_every_adapter() -> None:
    container = build_identity_access_container(_settings())

    assert isinstance(container.principal_port, KeyResolver)
    assert isinstance(container.api_key_admin, HashedApiKeyStore)
    assert isinstance(container.readiness, AlwaysReadyReadiness)
    assert isinstance(container.demo_policy, LoopbackDemoPolicy)


def test_postgres_without_a_database_is_refused() -> None:
    with pytest.raises(ValueError, match="PERSISTENCE=postgres"):
        build_identity_access_container(_settings(persistence=Persistence.POSTGRES))


def test_postgres_container_binds_the_uow_store_and_db_readiness() -> None:
    database = Database(_settings(persistence=Persistence.POSTGRES))
    try:
        container = build_identity_access_container(
            _settings(persistence=Persistence.POSTGRES), database
        )

        assert isinstance(container.api_key_admin, HashedApiKeyStore)
        assert isinstance(container.readiness, DatabaseReadiness)
    finally:
        asyncio.run(database.dispose())


def test_app_exposes_the_container_and_admin_routes() -> None:
    app = create_app(_settings())

    assert isinstance(app.state.identity_access.principal_port, KeyResolver)
    assert "/api/v1/admin/keys" in app.openapi()["paths"]


def test_admin_routes_declare_the_admin_scope() -> None:
    app = FastAPI()
    app.include_router(admin_router)
    paths = app.openapi()["paths"]

    assert paths["/api/v1/admin/keys"]["post"]["x-required-scope"] == "admin"
    assert paths["/api/v1/admin/keys"]["get"]["x-required-scope"] == "admin"
    assert paths["/api/v1/admin/keys/{key_id}"]["delete"]["x-required-scope"] == "admin"


def test_every_api_v1_route_declares_a_scope() -> None:
    app = create_app(_settings(auth_mode=AuthMode.STRICT))
    paths = app.openapi()["paths"]

    missing = []
    for path, operations in paths.items():
        if not path.startswith("/api/v1"):
            continue
        for method, operation in operations.items():
            if method not in HTTP_METHODS:
                continue
            if not operation.get("x-required-scope"):
                missing.append(f"{method.upper()} {path}")

    assert missing == []


async def test_every_api_v1_route_rejects_an_unscoped_principal() -> None:
    app = create_app(_settings(auth_mode=AuthMode.STRICT))
    app.state.identity_access = SimpleNamespace(
        principal_port=StaticPrincipalResolver(
            {"noscope": Principal(label="noscope", role=Role.ANALYST, scopes=frozenset())}
        )
    )
    paths = app.openapi()["paths"]
    transport = httpx.ASGITransport(app=app, raise_app_exceptions=False)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        for path, operations in paths.items():
            if not path.startswith("/api/v1"):
                continue
            concrete = re.sub(r"\{[^}]+\}", "x", path)
            for method in operations:
                if method not in HTTP_METHODS:
                    continue
                response = await client.request(
                    method.upper(),
                    concrete,
                    headers={"X-API-Key": "noscope"},
                )
                assert response.status_code == 403, (method, concrete, response.text)
                assert response.json()["code"] == "SCOPE_REQUIRED"
