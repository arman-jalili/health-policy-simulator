"""Contract freeze: wiring obligations (issue #331, implements #349).

The router, the container shape and the composition factory are frozen. The factory takes every
gate as a required keyword argument, so publication cannot be booted with a gate skipped (AC 11).
"""

from __future__ import annotations

import asyncio
import inspect
from typing import Any, cast

import pytest
from fastapi import Request
from tests.unit.decision_brief_contract_helpers import (
    SRC,
    annotation_names,
    domain_python_files,
    field_names,
    imported_modules,
    parameter_names,
)

from decision_brief.composition import DecisionBriefContainer, build_container
from decision_brief.domain.errors import BriefGateUnavailable
from decision_brief.interfaces.http.deps import (
    DecisionBriefContainer as HttpContainer,
)
from decision_brief.interfaces.http.deps import get_container
from decision_brief.interfaces.http.router import publish_decision_brief, router

CONTAINER_FIELDS = [
    "publish_decision_brief",
    "version_decision_brief",
    "get_decision_brief",
    "list_brief_versions",
    "list_citations",
    "renderer",
]


def _routes() -> dict[tuple[str, str], Any]:
    return {
        (method, getattr(route, "path", "")): route
        for route in router.routes
        for method in getattr(route, "methods", set())
    }


def test_http_contract_is_exact() -> None:
    expected = {
        ("POST", "/api/v1/runs/{run_id}/brief"),
        ("GET", "/api/v1/briefs/{brief_id}"),
        ("GET", "/api/v1/runs/{run_id}/briefs"),
        ("POST", "/api/v1/briefs/{brief_id}:version"),
        ("GET", "/api/v1/briefs/{brief_id}/citations"),
    }
    assert set(_routes()) == expected


def test_publication_and_versioning_answer_201() -> None:
    routes = _routes()
    assert routes[("POST", "/api/v1/runs/{run_id}/brief")].status_code == 201
    assert routes[("POST", "/api/v1/briefs/{brief_id}:version")].status_code == 201


def test_every_route_declares_the_scope_the_gate_enforces() -> None:
    for (method, path), route in _routes().items():
        expected = "briefs:publish" if method == "POST" else "runs:read"
        assert route.openapi_extra == {"x-required-scope": expected}, path


def test_the_handler_surface_is_still_a_stub() -> None:
    async def _call() -> None:
        await publish_decision_brief("run_01J")

    with pytest.raises(NotImplementedError):
        asyncio.run(_call())


def test_container_shape_is_frozen_in_both_representations() -> None:
    assert annotation_names(HttpContainer) == CONTAINER_FIELDS
    assert field_names(DecisionBriefContainer) == CONTAINER_FIELDS


def test_the_factory_names_every_port_and_requires_every_gate() -> None:
    assert parameter_names(build_container) == [
        "settings",
        "database",
        "briefs",
        "history",
        "consensus",
        "citations",
        "provenance",
        "projection",
        "disclaimer",
        "events",
        "clock",
        "ids",
        "uow",
        "renderer",
    ]
    parameters = inspect.signature(build_container).parameters
    for gate in ("citations", "provenance"):
        assert parameters[gate].default is inspect.Parameter.empty, gate


def test_an_unmounted_container_fails_closed() -> None:
    class _State:
        pass

    class _App:
        def __init__(self) -> None:
            self.state = _State()

    class _Request:
        def __init__(self) -> None:
            self.app = _App()

    with pytest.raises(BriefGateUnavailable):
        get_container(cast(Request, _Request()))


def test_the_domain_layer_imports_no_outer_layer_or_foreign_context() -> None:
    forbidden_prefixes = (
        "decision_brief.application",
        "decision_brief.infrastructure",
        "decision_brief.interfaces",
    )
    allowed_roots = {
        "__future__",
        "collections",
        "dataclasses",
        "datetime",
        "enum",
        "shared",
        "types",
        "typing",
    }
    for path in domain_python_files():
        relative = path.relative_to(SRC.parent).as_posix().removeprefix("decision_brief/")
        for module in imported_modules(relative):
            assert not module.startswith(forbidden_prefixes), f"{relative} imports {module}"
            assert module.split(".")[0] in allowed_roots or module.startswith(
                "decision_brief.domain"
            ), f"{relative} imports {module}"
