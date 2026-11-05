"""Contract freeze: readiness reports every dependency and health stays auth-free."""

from __future__ import annotations

from fastapi.routing import APIRoute

from identity_access.interfaces.dto import ReadinessCheck, ReadinessReport
from identity_access.interfaces.ports import ReadinessPort
from shared.http.health import router as health_router


def test_readiness_is_false_when_any_dependency_fails() -> None:
    checks = (
        ReadinessCheck(name="database", ok=True),
        ReadinessCheck(name="llm", ok=False, detail="timeout"),
    )
    report = ReadinessReport(ready=all(check.ok for check in checks), checks=checks)

    assert report.ready is False
    assert [check.name for check in report.checks] == ["database", "llm"]


def test_readiness_port_exposes_check() -> None:
    assert hasattr(ReadinessPort, "check")


def test_health_routes_are_auth_free() -> None:
    routes = [route for route in health_router.routes if isinstance(route, APIRoute)]
    paths = {route.path for route in routes}

    assert {"/healthz", "/readyz"} <= paths
    for route in routes:
        assert route.dependencies == []
