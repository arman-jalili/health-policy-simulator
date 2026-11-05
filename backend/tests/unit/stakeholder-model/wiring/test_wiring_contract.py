"""Contract freeze: the HTTP surface and its runtime container shape."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from shared.app import create_app
from shared.config import Settings
from shared.enums import Persistence
from stakeholder_model.composition import build_container as build_stakeholder_container
from stakeholder_model.interfaces.http.deps import StakeholderModelContainer, get_container
from stakeholder_model.interfaces.http.router import router

EXPECTED_ROUTES = {
    ("GET", "/api/v1/stakeholders"),
    ("POST", "/api/v1/stakeholders"),
    ("PATCH", "/api/v1/stakeholders/{stakeholder_id}"),
    ("POST", "/api/v1/stakeholders/{stakeholder_id}/powers"),
    ("GET", "/api/v1/stakeholders/{stakeholder_id}/history"),
    ("POST", "/api/v1/stakeholders/{stakeholder_id}/history"),
    ("POST", "/api/v1/runs/{run_id}/stakeholders:select"),
    ("POST", "/api/v1/runs/{run_id}/stakeholders:bind"),
}


def test_router_exposes_exactly_the_frozen_routes() -> None:
    actual = {
        (method, route.path)
        for route in router.routes
        if hasattr(route, "methods") and hasattr(route, "path")
        for method in route.methods
        if method != "HEAD"
    }

    assert actual == EXPECTED_ROUTES
    assert router.prefix == "/api/v1"


def test_every_route_declares_its_scope() -> None:
    for route in router.routes:
        if not hasattr(route, "openapi_extra"):
            continue
        extra = route.openapi_extra or {}
        assert "x-required-scope" in extra


def test_container_binds_every_application_service() -> None:
    annotations = StakeholderModelContainer.__annotations__

    assert {
        "register_stakeholder",
        "update_profile",
        "cite_power_source",
        "record_position",
        "select_stakeholders",
        "bind_persona",
        "get_profile",
        "list_stakeholders",
        "list_positions",
        "load_personas",
        "publish_allowlist",
        "transaction",
    } <= set(annotations)
    assert callable(get_container)


DATABASE_URL = "postgresql+asyncpg://hps:hps@localhost:5433/health_policy"


def _settings() -> Settings:
    return Settings(
        _env_file=None,
        database_url=DATABASE_URL,
        persistence=Persistence.MEMORY,
    )


async def test_container_publishes_all_nine_institutions_to_the_guard() -> None:
    container = build_stakeholder_container(_settings())

    allowlist = await container.publish_allowlist.execute()

    assert len(container.personas) == 9
    assert len(allowlist.institutions) == 9
    assert container.guard.codes == {
        "aerztekammer",
        "apothekerkammer",
        "bmsgpk",
        "krankenhausgesellschaft",
        "landesgesundheitsfonds",
        "oegk",
        "patientenanwaltschaft",
        "privatkrankenanstalten",
        "sozialversicherung",
    }
    assert all(container.guard.recognises(code) for code in container.guard.codes)


def test_app_mounts_the_stakeholder_routes() -> None:
    app = create_app(_settings())

    paths = set(app.openapi()["paths"])

    assert "/api/v1/stakeholders" in paths
    assert "/api/v1/stakeholders/{stakeholder_id}" in paths
    assert "/api/v1/runs/{run_id}/stakeholders:select" in paths
    assert "/api/v1/runs/{run_id}/stakeholders:bind" in paths
    assert app.state.stakeholder_model is not None


def test_invalid_persona_aborts_container_boot(tmp_path: Path) -> None:
    source = Path("config/personas/oegk.yaml").read_text(encoding="utf-8")
    document = yaml.safe_load(source)
    document["code"] = "broken"
    document["interests"] = []
    (tmp_path / "broken.yaml").write_text(
        yaml.safe_dump(document, allow_unicode=True, sort_keys=False), encoding="utf-8"
    )

    with pytest.raises(ValueError, match="no interests"):
        build_stakeholder_container(_settings(), persona_directory=tmp_path)
