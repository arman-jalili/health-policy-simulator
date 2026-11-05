"""Contract freeze: the container exposes exactly four ports and admin routes are scoped."""

from __future__ import annotations

from dataclasses import fields

import pytest
from fastapi import FastAPI

from identity_access.composition import (
    IdentityAccessContainer,
    build_identity_access_container,
)
from identity_access.interfaces.http.router import router as admin_router
from shared.config import Settings
from shared.enums import Persistence

DATABASE_URL = "postgresql+asyncpg://hps:hps@localhost:5433/health_policy"


def _settings() -> Settings:
    return Settings(
        _env_file=None,
        database_url=DATABASE_URL,
        persistence=Persistence.MEMORY,
    )


def test_container_freezes_the_four_wired_ports() -> None:
    assert [field.name for field in fields(IdentityAccessContainer)] == [
        "principal_port",
        "api_key_admin",
        "readiness",
        "demo_policy",
    ]


def test_builder_is_a_contract_stub_until_the_wiring_issue() -> None:
    with pytest.raises(NotImplementedError, match="issue #41"):
        build_identity_access_container(_settings())


def test_admin_routes_declare_the_admin_scope() -> None:
    app = FastAPI()
    app.include_router(admin_router)
    document = app.openapi()
    paths = document["paths"]

    assert paths["/api/v1/admin/keys"]["post"]["x-required-scope"] == "admin"
    assert paths["/api/v1/admin/keys"]["get"]["x-required-scope"] == "admin"
    assert paths["/api/v1/admin/keys/{key_id}"]["delete"]["x-required-scope"] == "admin"
