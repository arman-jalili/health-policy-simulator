"""Contract freeze: SSE (issue #282, implements #298)."""

from __future__ import annotations

from typing import Any

from tests.unit.negotiation_session_contract_helpers import (
    field_names,
    method_names,
    parameter_names,
)

from negotiation_session.application.dto import ProgressEventResult
from negotiation_session.application.ports import RunProgressPublisher, RunProgressStream
from negotiation_session.application.progress import (
    SSE_LAST_EVENT_ID_HEADER,
    SSE_MEDIA_TYPE,
    SseFrame,
    encode_frame,
    parse_last_event_id,
)
from negotiation_session.interfaces.http.router import router


def _routes() -> dict[tuple[str, str], Any]:
    return {
        (method, getattr(route, "path", "")): route
        for route in router.routes
        for method in getattr(route, "methods", set())
    }


def test_stream_wire_contract_is_frozen() -> None:
    assert SSE_MEDIA_TYPE == "text/event-stream"
    assert SSE_LAST_EVENT_ID_HEADER == "Last-Event-ID"
    assert field_names(SseFrame) == ["event_id", "event", "data"]
    assert field_names(ProgressEventResult) == [
        "event_id",
        "run_id",
        "sequence",
        "event_type",
        "payload",
        "created_at",
    ]
    assert parameter_names(encode_frame) == ["frame"]
    assert parameter_names(parse_last_event_id) == ["value"]


def test_reconnect_replays_after_last_event_id() -> None:
    assert parameter_names(RunProgressStream.subscribe) == [
        "self",
        "run_id",
        "last_event_id",
    ]
    assert "publish" in method_names(RunProgressPublisher)
    stream = _routes()[("GET", "/api/v1/runs/{run_id}/negotiation/stream")]
    assert stream.openapi_extra == {"x-required-scope": "runs:read"}
