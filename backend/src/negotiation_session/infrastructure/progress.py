"""In-memory progress broker for the SSE contract (issues #298, #299).

Frames are ordered by a per-run sequence; ``subscribe`` replays every frame after
``Last-Event-ID`` (exclusive), so a reconnect receives a contiguous stream with no gap and no
duplicate. The production broker shares the SimulationOrchestration progress transport.
"""

from __future__ import annotations

import dataclasses
from collections.abc import AsyncIterator, Sequence

from negotiation_session.application.progress import SseFrame, parse_last_event_id
from negotiation_session.domain.events import DomainEvent
from negotiation_session.domain.values import RunId


def _payload(event: object) -> dict[str, object]:
    return {
        field.name: getattr(event, field.name)
        for field in dataclasses.fields(event)  # type: ignore[arg-type]
    }


class InMemoryProgressBroker:
    """Append-only per-run frame store with ``Last-Event-ID`` replay."""

    def __init__(self) -> None:
        self._frames: dict[RunId, list[SseFrame]] = {}

    async def publish(self, run_id: RunId, events: Sequence[DomainEvent]) -> None:
        frames = self._frames.setdefault(run_id, [])
        for event in events:
            sequence = len(frames) + 1
            frames.append(
                SseFrame(
                    event_id=str(sequence),
                    event=getattr(event, "name", type(event).__name__),
                    data=_payload(event),
                )
            )

    def subscribe(
        self, run_id: RunId, *, last_event_id: str | None = None
    ) -> AsyncIterator[SseFrame]:
        start = parse_last_event_id(last_event_id) or 0
        frames = list(self._frames.get(run_id, []))
        return self._replay(frames, start)

    async def _replay(self, frames: Sequence[SseFrame], start: int) -> AsyncIterator[SseFrame]:
        for frame in frames[start:]:
            yield frame
