"""Contract freeze: wiring and API surface (issue #282, implements #299)."""

from __future__ import annotations

from typing import Any

from tests.unit.negotiation_session_contract_helpers import (
    annotation_names,
    parameter_names,
)

from negotiation_session.composition import (
    NegotiationSessionContainer,
    build_container,
)
from negotiation_session.domain.errors import GovernanceGuardUnavailable
from negotiation_session.interfaces.http.deps import (
    NegotiationSessionContainer as HttpContainer,
)
from negotiation_session.interfaces.http.router import router


def _routes() -> dict[tuple[str, str], Any]:
    return {
        (method, getattr(route, "path", "")): route
        for route in router.routes
        for method in getattr(route, "methods", set())
    }


def test_http_contract_is_exact() -> None:
    routes = _routes()
    expected = {
        ("POST", "/api/v1/runs"),
        ("GET", "/api/v1/runs/{run_id}"),
        ("GET", "/api/v1/runs/{run_id}/events"),
        ("GET", "/api/v1/runs/{run_id}/rounds"),
        ("POST", "/api/v1/runs/{run_id}/rounds"),
        ("POST", "/api/v1/runs/{run_id}/rounds/{number}:close"),
        ("POST", "/api/v1/runs/{run_id}/positions"),
        ("POST", "/api/v1/runs/{run_id}/turns"),
        ("POST", "/api/v1/runs/{run_id}/positions/{position_id}:revise"),
        ("POST", "/api/v1/runs/{run_id}/abstentions"),
        ("GET", "/api/v1/runs/{run_id}/conflicts"),
        ("POST", "/api/v1/runs/{run_id}/coalitions"),
        ("GET", "/api/v1/runs/{run_id}/learning"),
        ("GET", "/api/v1/runs/{run_id}/stream"),
    }
    assert set(routes) == expected
    assert routes[("POST", "/api/v1/runs")].status_code == 202
    assert routes[("POST", "/api/v1/runs/{run_id}/rounds")].status_code == 201
    assert routes[("POST", "/api/v1/runs/{run_id}/positions")].status_code == 201
    assert routes[("POST", "/api/v1/runs/{run_id}/turns")].status_code == 201
    assert routes[("POST", "/api/v1/runs/{run_id}/abstentions")].status_code == 204
    assert routes[("POST", "/api/v1/runs/{run_id}/coalitions")].status_code == 201


def test_every_route_declares_its_scope() -> None:
    for (method, path), route in _routes().items():
        expected = "runs:write" if method == "POST" else "runs:read"
        assert route.openapi_extra == {"x-required-scope": expected}, path


def test_container_and_factory_are_frozen() -> None:
    assert annotation_names(NegotiationSessionContainer) == [
        "translate_question_to_mandate",
        "select_relevant_stakeholders",
        "open_simulation_run",
        "open_round",
        "submit_initial_position",
        "take_negotiation_turn",
        "revise_position",
        "record_abstention",
        "track_conflict_topic",
        "form_coalition",
        "close_round",
        "get_simulation_run",
        "list_rounds",
        "list_conflict_topics",
        "list_round_learning",
        "summarise_intermediate_result",
        "replay_simulation_history",
        "progress_stream",
    ]
    assert parameter_names(build_container) == [
        "settings",
        "database",
        "evidence",
        "stakeholders",
        "claims",
        "governance",
        "invocations",
        "progress",
    ]
    assert annotation_names(HttpContainer) == [
        "translate_question_to_mandate",
        "open_simulation_run",
        "open_round",
        "submit_initial_position",
        "take_negotiation_turn",
        "revise_position",
        "record_abstention",
        "track_conflict_topic",
        "form_coalition",
        "close_round",
        "get_simulation_run",
        "list_rounds",
        "list_conflict_topics",
        "list_round_learning",
        "summarise_intermediate_result",
        "replay_simulation_history",
        "progress_stream",
    ]


def test_missing_guard_fails_closed() -> None:
    assert GovernanceGuardUnavailable.code == "GOVERNANCE_GUARD_UNAVAILABLE"
