"""SSE wire contract for live runs (contract frozen, issue #282).

Canonical: ``.pi/architecture/modules/negotiation-session.md`` (API Endpoints, AC 13)

Frames are ordered by ``sequence``. ``event_id`` is the per-run ordinal rendered as a string, so
``Last-Event-ID`` replay is contiguous: the client receives every event after the supplied id
with no gap and no duplicate.
"""

from __future__ import annotations

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
    raise NotImplementedError("SSE frame encoding is implemented by issue #298")


def parse_last_event_id(value: str | None) -> int | None:
    """Return the ordinal encoded in ``Last-Event-ID``; ``None`` means "from the start"."""
    raise NotImplementedError("Last-Event-ID parsing is implemented by issue #298")
