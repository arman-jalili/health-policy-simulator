"""End-to-end runtime proof for NegotiationSession (issue #300, ADR-015).

Runs against the real application shell (memory persistence family) with every ACL port bound to
its upstream context: open a run, read its state, replay `/events` and stream ordered frames.
"""

from __future__ import annotations

from typing import Any

import httpx
from fastapi import FastAPI

from negotiation_session.interfaces.http.router import router as negotiation_router


def _route_paths() -> set[str]:
    return {getattr(route, "path", "") for route in negotiation_router.routes}


async def test_the_public_api_reaches_the_wired_negotiation_session(
    app: FastAPI, client: httpx.AsyncClient
) -> None:
    paths = _route_paths()
    assert "/api/v1/runs" in paths
    assert "/api/v1/runs/{run_id}" in paths
    assert "/api/v1/runs/{run_id}/events" in paths
    assert "/api/v1/runs/{run_id}/stream" in paths
    assert hasattr(app.state, "negotiation_session")

    opened = await client.post(
        "/api/v1/runs",
        json={"question": "How do we stabilise Austrian healthcare costs?", "round_cap": 3},
    )
    assert opened.status_code == 202, opened.text
    run_id = opened.json()["run_id"]

    state = await client.get(f"/api/v1/runs/{run_id}")
    assert state.status_code == 200
    assert state.json()["phase"] == "position_formation"

    replay = await client.get(f"/api/v1/runs/{run_id}/events")
    assert replay.status_code == 200
    body = replay.json()
    assert body["items"][0]["event_type"] == "SimulationRunOpened"
    assert body["state"]["run_id"] == run_id


async def test_the_acl_ports_are_bound_to_real_upstream_contexts(app: FastAPI) -> None:
    container = app.state.negotiation_session
    assert container.progress_stream is not None
    assert app.state.evidence_retrieval is not None
    assert app.state.stakeholder_model is not None
    assert app.state.governance_compliance is not None


async def test_round_lifecycle_opens_closes_and_closes_the_run(
    app: FastAPI, client: httpx.AsyncClient
) -> None:
    opened = await client.post(
        "/api/v1/runs",
        json={"question": "Can a round close?", "round_cap": 1},
    )
    assert opened.status_code == 202, opened.text
    run_id = opened.json()["run_id"]
    stakeholders = [item["stakeholder_id"] for item in opened.json()["bound"]]

    round_response = await client.post(f"/api/v1/runs/{run_id}/rounds")
    assert round_response.status_code == 201, round_response.text
    assert round_response.json()["round"] == 1

    duplicate = await client.post(f"/api/v1/runs/{run_id}/rounds")
    assert duplicate.status_code == 409
    assert duplicate.json()["code"] == "ROUND_STILL_OPEN"

    for stakeholder in stakeholders:
        abstained = await client.post(
            f"/api/v1/runs/{run_id}/abstentions",
            json={"stakeholder_id": stakeholder, "topic": "Can a round close?"},
        )
        assert abstained.status_code == 204, abstained.text

    closed = await client.post(
        f"/api/v1/runs/{run_id}/rounds/1:close",
        json={"learning": [], "convergence": "none"},
    )
    assert closed.status_code == 200, closed.text
    assert closed.json()["stopping_condition"]["fired"] is True
    assert closed.json()["stopping_condition"]["name"] == "round_cap"

    state = await client.get(f"/api/v1/runs/{run_id}")
    assert state.json()["closed"] is True
    events = await client.get(f"/api/v1/runs/{run_id}/events")
    types = [item["event_type"] for item in events.json()["items"]]
    assert types[-4:] == [
        "RoundLearningCaptured",
        "RoundClosed",
        "NegotiationPhaseAdvanced",
        "SimulationRunClosed",
    ]


async def test_closing_a_run_notifies_consensus_without_an_extra_api_call(
    app: FastAPI, client: httpx.AsyncClient
) -> None:
    called: list[Any] = []

    async def fake_execute(request: object) -> None:
        called.append(request)

    app.state.consensus_analysis.handle_run_closed.execute = fake_execute

    opened = await client.post(
        "/api/v1/runs",
        json={
            "question": "Notify consensus?",
            "round_cap": 1,
            "stakeholder_ids": ["stk_aerztekammer"],
        },
    )
    assert opened.status_code == 202, opened.text
    run_id = opened.json()["run_id"]
    assert (await client.post(f"/api/v1/runs/{run_id}/rounds")).status_code == 201
    abstained = await client.post(
        f"/api/v1/runs/{run_id}/abstentions",
        json={"stakeholder_id": "stk_aerztekammer", "topic": "Notify consensus?"},
    )
    assert abstained.status_code == 204
    closed = await client.post(
        f"/api/v1/runs/{run_id}/rounds/1:close",
        json={"learning": [], "convergence": "none"},
    )

    assert closed.status_code == 200, closed.text
    assert len(called) == 1
    assert str(called[0].run_id) == run_id
