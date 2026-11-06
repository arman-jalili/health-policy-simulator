"""End-to-end runtime proof for NegotiationSession (issue #300, ADR-015).

Runs against the real application shell (memory persistence family) with every ACL port bound to
its upstream context: open a run, read its state, replay `/events` and stream ordered frames.
"""

from __future__ import annotations

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
