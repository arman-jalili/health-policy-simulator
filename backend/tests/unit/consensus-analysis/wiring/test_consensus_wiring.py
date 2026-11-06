"""Contract freeze: wiring and the API surface (issue #305, implements #320)."""

from __future__ import annotations

from typing import Any

from tests.unit.consensus_analysis_contract_helpers import (
    SRC,
    annotation_names,
    domain_python_files,
    imported_modules,
    parameter_names,
)

from consensus_analysis.application.services import HandleRunClosed
from consensus_analysis.composition import ConsensusAnalysisContainer, build_container
from consensus_analysis.interfaces.http.deps import (
    ConsensusAnalysisContainer as HttpContainer,
)
from consensus_analysis.interfaces.http.router import router


def _routes() -> dict[tuple[str, str], Any]:
    return {
        (method, getattr(route, "path", "")): route
        for route in router.routes
        for method in getattr(route, "methods", set())
    }


def test_http_contract_is_exact() -> None:
    routes = _routes()
    expected = {
        ("POST", "/api/v1/runs/{run_id}/analysis:derive"),
        ("GET", "/api/v1/runs/{run_id}/consensus"),
        ("GET", "/api/v1/runs/{run_id}/conflicts/open"),
        ("POST", "/api/v1/runs/{run_id}/packages"),
        ("GET", "/api/v1/runs/{run_id}/packages"),
        ("POST", "/api/v1/packages/{package_id}/scenarios"),
        ("GET", "/api/v1/packages/{package_id}/comparison"),
    }
    assert set(routes) == expected
    assert routes[("POST", "/api/v1/runs/{run_id}/packages")].status_code == 201
    assert routes[("POST", "/api/v1/packages/{package_id}/scenarios")].status_code == 201
    assert routes[("POST", "/api/v1/runs/{run_id}/analysis:derive")].status_code is None
    assert routes[("GET", "/api/v1/runs/{run_id}/consensus")].status_code is None


def test_every_route_declares_its_scope() -> None:
    for (method, path), route in _routes().items():
        expected = "runs:write" if method == "POST" else "runs:read"
        assert route.openapi_extra == {"x-required-scope": expected}, path


def test_container_and_factory_are_frozen() -> None:
    assert annotation_names(ConsensusAnalysisContainer) == [
        "derive_consensus",
        "get_consensus",
        "list_unresolved_conflicts",
        "compose_compromise_package",
        "list_packages",
        "assess_impact",
        "compare_scenarios",
        "rebuild_projections",
        "handle_run_closed",
    ]
    assert annotation_names(HttpContainer) == annotation_names(ConsensusAnalysisContainer)
    assert parameter_names(build_container) == [
        "settings",
        "database",
        "consensus",
        "packages",
        "scenarios",
        "log",
        "powers",
        "estimation",
        "catalogue",
        "llm",
        "rebuilder",
        "ranker",
        "events",
    ]


def test_the_run_closed_subscriber_is_a_thin_entry_point() -> None:
    """One collaborator only: the derivation use case it delegates to (AC 12)."""
    assert parameter_names(HandleRunClosed.execute) == ["self", "request"]
    subscriber = HandleRunClosed(derive=None)  # type: ignore[arg-type]
    assert len(subscriber.collaborators()) == 1


def test_the_domain_layer_imports_no_outer_layer() -> None:
    forbidden_prefixes = (
        "consensus_analysis.application",
        "consensus_analysis.infrastructure",
        "consensus_analysis.interfaces",
    )
    for path in domain_python_files():
        relative = path.relative_to(SRC).as_posix()
        for module in imported_modules(relative):
            assert not module.startswith(forbidden_prefixes), f"{relative} imports {module}"
            assert module.split(".")[0] in {
                "__future__",
                "collections",
                "dataclasses",
                "datetime",
                "decimal",
                "enum",
                "hashlib",
                "json",
                "shared",
                "typing",
            } or module.startswith("consensus_analysis.domain"), f"{relative} imports {module}"
