"""Wiring: the negotiation API is mounted and the run log replays (issue #299)."""

from __future__ import annotations

import httpx
import pytest
from fastapi import FastAPI

from negotiation_session.application.ports import RunProgressStream
from negotiation_session.domain.errors import GovernanceGuardUnavailable
from negotiation_session.domain.values import RunId, StakeholderId
from negotiation_session.infrastructure.acl import GovernanceGuardAdapter
from negotiation_session.interfaces.http.router import stream_run


async def test_a_run_can_be_opened_and_replayed_through_the_public_api(
    client: httpx.AsyncClient, app: FastAPI
) -> None:
    opened = await client.post(
        "/api/v1/runs", json={"question": "How do we stabilise costs?", "round_cap": 4}
    )
    assert opened.status_code == 202, opened.text
    body = opened.json()
    run_id = body["run_id"]
    assert body["phase"] == "position_formation"
    assert body["bound"], "the run must bind at least one registered institution"

    state = await client.get(f"/api/v1/runs/{run_id}")
    assert state.status_code == 200
    assert state.json()["run_id"] == run_id
    assert state.json()["closed"] is False

    events = await client.get(f"/api/v1/runs/{run_id}/events")
    assert events.status_code == 200
    payload = events.json()
    assert next(item["event_type"] for item in payload["items"]) == "SimulationRunOpened"
    assert payload["state"]["run_id"] == run_id

    stream: RunProgressStream = app.state.negotiation_session.progress_stream
    response = await stream_run(run_id, app.state.negotiation_session, None)
    assert response.media_type == "text/event-stream"
    rendered = "".join(
        [
            bytes(chunk).decode() if not isinstance(chunk, str) else chunk
            async for chunk in response.body_iterator
        ]
    )
    assert "event: SimulationRunOpened" in rendered
    assert stream is not None


async def test_reconnect_with_last_event_id_replays_without_duplicates(
    client: httpx.AsyncClient, app: FastAPI
) -> None:
    opened = await client.post("/api/v1/runs", json={"question": "Access reform?"})
    run_id = opened.json()["run_id"]
    response = await stream_run(run_id, app.state.negotiation_session, "1")
    rendered = "".join(
        [
            bytes(chunk).decode() if not isinstance(chunk, str) else chunk
            async for chunk in response.body_iterator
        ]
    )
    assert rendered == ""


async def test_an_invalid_last_event_id_is_a_bad_request(app: FastAPI) -> None:
    from shared.errors import BadRequestError

    with pytest.raises(BadRequestError):
        await stream_run("run_1", app.state.negotiation_session, "not-a-number")


async def test_a_missing_guard_fails_closed(app: FastAPI) -> None:
    unbound = GovernanceGuardAdapter(None)
    with pytest.raises(GovernanceGuardUnavailable):
        await unbound.enforce(
            "text",
            run_id=RunId("run_1"),
            stakeholder_id=StakeholderId("stk_a"),
        )
    assert app.state.negotiation_session.progress_stream is not None
