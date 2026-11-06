"""Contract freeze: wiring and API surface (issue #205)."""

from __future__ import annotations

from typing import Any

from tests.unit.simulation_orchestration_contract_helpers import (
    annotation_names,
    method_names,
    parameter_names,
)

from simulation_orchestration.application.errors import UnknownModel
from simulation_orchestration.application.ports import WorkerLoop
from simulation_orchestration.composition import (
    SimulationOrchestrationContainer,
    build_container,
)
from simulation_orchestration.interfaces.http.deps import (
    SimulationOrchestrationContainer as HttpContainer,
)
from simulation_orchestration.interfaces.http.router import router


def _routes() -> dict[tuple[str, str], Any]:
    return {
        (method, getattr(route, "path", "")): route
        for route in router.routes
        for method in getattr(route, "methods", set())
    }


def test_http_contract_is_exact() -> None:
    routes = _routes()
    assert routes
    expected = {
        ("POST", "/api/v1/runs/{run_id}:start"),
        ("GET", "/api/v1/runs/{run_id}/stream"),
        ("POST", "/api/v1/runs/{run_id}:pause"),
        ("POST", "/api/v1/runs/{run_id}:resume"),
        ("GET", "/api/v1/runs/{run_id}/usage"),
        ("GET", "/api/v1/jobs/{job_id}"),
    }
    assert set(routes) == expected
    assert _routes()[("POST", "/api/v1/runs/{run_id}:start")].status_code == 202
    assert _routes()[("POST", "/api/v1/runs/{run_id}:pause")].status_code == 202
    assert _routes()[("POST", "/api/v1/runs/{run_id}:resume")].status_code == 202


def test_write_routes_declare_runs_write_scope() -> None:
    start = _routes()[("POST", "/api/v1/runs/{run_id}:start")]
    assert start.openapi_extra == {"x-required-scope": "runs:write"}
    stream = _routes()[("GET", "/api/v1/runs/{run_id}/stream")]
    assert stream.openapi_extra == {"x-required-scope": "runs:read"}


def test_container_and_factory_are_frozen() -> None:
    assert annotation_names(SimulationOrchestrationContainer) == [
        "run_simulation_job",
        "stream_simulation_progress",
        "pause_or_resume_simulation",
        "record_agent_invocation",
        "get_job",
        "collect_usage_report",
        "register_prompt_template",
        "resolve_prompt_template",
        "worker",
        "model",
        "provider",
    ]
    assert parameter_names(build_container) == ["settings", "database", "negotiation"]
    assert annotation_names(HttpContainer) == [
        "run_simulation_job",
        "stream_simulation_progress",
        "pause_or_resume_simulation",
        "get_job",
        "collect_usage_report",
        "model",
        "provider",
    ]


def test_worker_and_boot_failure_contracts_are_frozen() -> None:
    assert {"run_forever", "run_once", "recover", "run_supervised"} <= method_names(WorkerLoop)
    assert UnknownModel.code == "UNKNOWN_MODEL"
