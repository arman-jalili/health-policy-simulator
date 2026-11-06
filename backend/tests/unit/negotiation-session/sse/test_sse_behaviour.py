"""SSE frame encoding and contiguous Last-Event-ID replay (issue #298)."""

from __future__ import annotations

import json

import pytest

from negotiation_session.application.progress import (
    SSE_LAST_EVENT_ID_HEADER,
    SSE_MEDIA_TYPE,
    SseFrame,
    encode_frame,
    parse_last_event_id,
)
from negotiation_session.domain.events import RoundOpened, SimulationRunOpened
from negotiation_session.domain.values import NegotiationPhase, RunId, StakeholderId
from negotiation_session.infrastructure.progress import InMemoryProgressBroker

RUN = RunId("run_1")


def test_a_frame_is_rendered_as_a_spec_compliant_event_stream_entry() -> None:
    frame = SseFrame(event_id="7", event="RoundOpened", data={"round": 2, "phase": "debate"})
    rendered = encode_frame(frame)
    assert SSE_MEDIA_TYPE == "text/event-stream"
    assert SSE_LAST_EVENT_ID_HEADER == "Last-Event-ID"
    assert rendered.startswith("id: 7\nevent: RoundOpened\ndata: ")
    assert rendered.endswith("\n\n")
    data_line = rendered.splitlines()[2]
    assert json.loads(data_line.removeprefix("data: ")) == {"round": 2, "phase": "debate"}


def test_last_event_id_parsing_is_strict() -> None:
    assert parse_last_event_id(None) is None
    assert parse_last_event_id("") is None
    assert parse_last_event_id("3") == 3
    with pytest.raises(ValueError):
        parse_last_event_id("not-a-number")
    with pytest.raises(ValueError):
        parse_last_event_id("-1")


async def _events() -> list[SimulationRunOpened | RoundOpened]:
    return [
        SimulationRunOpened(
            run_id=RUN,
            mandate_hash="hash",
            snapshot_id="snap",
            stakeholder_ids=(StakeholderId("stk_a"),),
        ),
        RoundOpened(
            run_id=RUN,
            round=1,
            turn_order=(StakeholderId("stk_a"),),
            phase=NegotiationPhase.POSITION_FORMATION,
        ),
        RoundOpened(
            run_id=RUN,
            round=2,
            turn_order=(StakeholderId("stk_a"),),
            phase=NegotiationPhase.DEBATE,
        ),
    ]


async def test_a_live_run_emits_ordered_frames() -> None:
    broker = InMemoryProgressBroker()
    await broker.publish(RUN, await _events())
    frames = [frame async for frame in broker.subscribe(RUN)]
    assert [frame.event_id for frame in frames] == ["1", "2", "3"]
    assert [frame.event for frame in frames] == [
        "SimulationRunOpened",
        "RoundOpened",
        "RoundOpened",
    ]
    assert frames[2].data["round"] == 2


async def test_reconnecting_after_last_event_id_replays_without_gaps_or_duplicates() -> None:
    broker = InMemoryProgressBroker()
    await broker.publish(RUN, await _events())
    replayed = [frame async for frame in broker.subscribe(RUN, last_event_id="1")]
    assert [frame.event_id for frame in replayed] == ["2", "3"]
    assert [frame.data["round"] for frame in replayed] == [1, 2]
    nothing = [frame async for frame in broker.subscribe(RUN, last_event_id="3")]
    assert nothing == []
