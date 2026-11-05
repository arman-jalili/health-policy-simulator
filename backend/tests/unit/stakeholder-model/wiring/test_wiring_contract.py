"""Contract freeze: the HTTP surface and its runtime container shape."""

from __future__ import annotations

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
