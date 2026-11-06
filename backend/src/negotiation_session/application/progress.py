"""SSE wire contract for live runs (contract frozen, issue #282).

Canonical: ``.pi/architecture/modules/negotiation-session.md`` (API Endpoints, AC 13)

Frames are ordered by ``sequence``. ``event_id`` is the per-run ordinal rendered as a string, so
``Last-Event-ID`` replay is contiguous: the client receives every event after the supplied id
with no gap and no duplicate.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass

SSE_MEDIA_TYPE = "text/event-stream"
SSE_LAST_EVENT_ID_HEADER = "Last-Event-ID"
SSE_DEFAULT_EVENT = "message"


@dataclass(frozen=True, slots=True)
class SseFrame:
    """One ``text/event-stream`` frame; ``data`` is the JSON payload body."""

    event_id: str
    event: str
    data: Mapping[str, object]


def encode_frame(frame: SseFrame) -> str:
    """Render one spec-compliant frame with its id, event name and JSON data line."""
    payload = json.dumps(dict(frame.data), default=str, sort_keys=True)
    return f"id: {frame.event_id}\nevent: {frame.event}\ndata: {payload}\n\n"


def parse_last_event_id(value: str | None) -> int | None:
    """Return the ordinal encoded in ``Last-Event-ID``; ``None`` means "from the start"."""
    if value is None or not value.strip():
        return None
    try:
        ordinal = int(value)
    except ValueError as error:
        raise ValueError(f"invalid Last-Event-ID: {value!r}") from error
    if ordinal < 0:
        raise ValueError(f"invalid Last-Event-ID: {value!r}")
    return ordinal
