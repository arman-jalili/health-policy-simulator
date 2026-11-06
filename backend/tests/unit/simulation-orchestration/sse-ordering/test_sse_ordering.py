"""Contract freeze: SSE ordering (issue #205)."""

from __future__ import annotations

import asyncio
import inspect
from collections.abc import AsyncGenerator
from typing import cast

from tests.unit.simulation_orchestration_contract_helpers import (
    enum_values,
    field_names,
    method_names,
    parameter_names,
)

from simulation_orchestration.application.dto import ProgressEventView
from simulation_orchestration.application.repositories import ProgressStore
from simulation_orchestration.application.services import StreamSimulationProgress
from simulation_orchestration.application.values import ProgressKind


def test_progress_event_has_monotonic_sequence_and_replay_id() -> None:
    assert field_names(ProgressEventView) == [
        "event_id",
        "run_id",
        "sequence",
        "kind",
        "payload",
        "created_at",
    ]
    assert enum_values(ProgressKind) >= {
        "run.started",
        "run.paused",
        "run.resumed",
        "run.completed",
        "run.failed",
        "run.budget_exhausted",
    }


def test_progress_store_replays_after_sequence() -> None:
    assert method_names(ProgressStore) == {"append", "get", "latest_sequence", "list_after"}
    assert parameter_names(ProgressStore.list_after) == [
        "self",
        "run_id",
        "after_sequence",
        "limit",
    ]


def test_stream_returns_an_async_iterator() -> None:
    signature = inspect.signature(StreamSimulationProgress.execute)
    assert "AsyncIterator" in str(signature.return_annotation)


# --- behaviour: ordered replay with Last-Event-ID (issue #213) ------------------------------

from datetime import UTC, datetime  # noqa: E402

import pytest  # noqa: E402

from simulation_orchestration.application.commands import (  # noqa: E402
    StreamSimulationProgressRequest,
)
from simulation_orchestration.application.values import (  # noqa: E402
    EventId,
    RunId,
)
from simulation_orchestration.infrastructure.memory import (  # noqa: E402
    InMemoryProgressStore,
)


class _Clock:
    def now(self) -> datetime:
        return datetime(2026, 11, 6, tzinfo=UTC)


async def _seeded(count: int = 3) -> InMemoryProgressStore:
    store = InMemoryProgressStore()
    for sequence in range(1, count + 1):
        await store.append(
            ProgressEventView(
                event_id=str(EventId(f"evt_{sequence}")),
                run_id=RunId("run_1"),
                sequence=sequence,
                kind=ProgressKind.STARTED,
                payload={"n": sequence},
                created_at=_Clock().now(),
            )
        )
    return store


async def _collect(
    stream: AsyncGenerator[ProgressEventView | str, None],
) -> list[ProgressEventView | str]:
    return [frame async for frame in stream]


def _real(frames: list[ProgressEventView | str]) -> list[ProgressEventView]:
    return [
        frame
        for frame in frames
        if isinstance(frame, ProgressEventView) and frame.kind is not ProgressKind.STREAM_CLOSED
    ]


async def test_stream_replays_in_monotonic_order() -> None:
    store = await _seeded()
    service = StreamSimulationProgress(progress=store, idle_timeout_s=0.1, heartbeat_s=0)

    frames = [
        event
        async for event in service.execute(StreamSimulationProgressRequest(run_id=RunId("run_1")))
    ]
    events = _real(frames)

    assert [event.sequence for event in events] == [1, 2, 3]
    assert isinstance(frames[-1], ProgressEventView)
    assert frames[-1].kind is ProgressKind.STREAM_CLOSED
    assert frames[-1].payload == {"reason": "max_idle"}


async def test_last_event_id_replays_without_gaps_or_duplicates() -> None:
    store = await _seeded()
    service = StreamSimulationProgress(progress=store, idle_timeout_s=0.1, heartbeat_s=0)

    frames = [
        event
        async for event in service.execute(
            StreamSimulationProgressRequest(run_id=RunId("run_1"), last_event_id="evt_1")
        )
    ]

    assert [event.sequence for event in _real(frames)] == [2, 3]


async def test_batching_preserves_order() -> None:
    store = await _seeded(5)
    service = StreamSimulationProgress(progress=store, idle_timeout_s=0.1, heartbeat_s=0)

    frames = [
        event
        async for event in service.execute(
            StreamSimulationProgressRequest(run_id=RunId("run_1"), limit=2)
        )
    ]

    assert [event.sequence for event in _real(frames)] == [1, 2, 3, 4, 5]


async def test_unknown_last_event_id_is_rejected() -> None:
    store = await _seeded()
    service = StreamSimulationProgress(progress=store, idle_timeout_s=0.1, heartbeat_s=0)
    from simulation_orchestration.application.errors import UnknownLastEventId

    with pytest.raises(UnknownLastEventId, match="unknown Last-Event-ID"):
        await service.validate(
            StreamSimulationProgressRequest(run_id=RunId("run_1"), last_event_id="evt_missing")
        )


async def test_duplicate_sequence_is_rejected() -> None:
    store = await _seeded(1)
    duplicate = ProgressEventView(
        event_id="evt_other",
        run_id=RunId("run_1"),
        sequence=1,
        kind=ProgressKind.STARTED,
        payload={},
        created_at=_Clock().now(),
    )

    with pytest.raises(ValueError, match="duplicate progress sequence"):
        await store.append(duplicate)


async def test_unknown_last_event_id_is_rejected_before_streaming() -> None:
    from simulation_orchestration.application.errors import UnknownLastEventId
    from simulation_orchestration.application.services import StreamSimulationProgress
    from simulation_orchestration.infrastructure.memory import InMemoryProgressStore

    service = StreamSimulationProgress(progress=InMemoryProgressStore())
    request = StreamSimulationProgressRequest(run_id=RunId("run_1"), last_event_id="evt_nope")

    with pytest.raises(UnknownLastEventId) as raised:
        await service.validate(request)
    assert raised.value.status_code == 400
    assert raised.value.code == "UNKNOWN_LAST_EVENT_ID"


async def test_stream_stays_live_until_a_terminal_event() -> None:
    from simulation_orchestration.application.services import StreamSimulationProgress
    from simulation_orchestration.application.values import ProgressKind
    from simulation_orchestration.infrastructure.memory import InMemoryProgressStore

    store = InMemoryProgressStore()
    await store.append(
        ProgressEventView(
            event_id="evt_start",
            run_id=RunId("run_live"),
            sequence=0,
            kind=ProgressKind.STARTED,
            payload={},
            created_at=datetime.now(tz=UTC),
        )
    )
    stream = StreamSimulationProgress(progress=store, idle_timeout_s=1.0, heartbeat_s=0).execute(
        StreamSimulationProgressRequest(run_id=RunId("run_live"))
    )
    first = await anext(stream)
    assert not isinstance(first, str)
    assert first.kind is ProgressKind.STARTED

    await store.append(
        ProgressEventView(
            event_id="evt_done",
            run_id=RunId("run_live"),
            sequence=0,
            kind=ProgressKind.COMPLETED,
            payload={},
            created_at=datetime.now(tz=UTC),
        )
    )
    second = await anext(stream)
    assert not isinstance(second, str)
    assert second.kind is ProgressKind.COMPLETED
    closed = await anext(stream)
    assert not isinstance(closed, str)
    assert closed.kind is ProgressKind.STREAM_CLOSED
    assert closed.payload == {"reason": "run.completed"}


async def test_stream_does_not_close_at_the_old_half_second_cutoff() -> None:
    from simulation_orchestration.application.values import ProgressKind
    from simulation_orchestration.infrastructure.memory import InMemoryProgressStore

    store = InMemoryProgressStore()
    await store.append(
        ProgressEventView(
            event_id="evt_start",
            run_id=RunId("run_slow"),
            sequence=1,
            kind=ProgressKind.STARTED,
            payload={},
            created_at=datetime.now(tz=UTC),
        )
    )
    stream = cast(
        AsyncGenerator[ProgressEventView | str, None],
        StreamSimulationProgress(progress=store, idle_timeout_s=2.0, heartbeat_s=0.05).execute(
            StreamSimulationProgressRequest(run_id=RunId("run_slow"))
        ),
    )
    first = await anext(stream)
    assert not isinstance(first, str)
    rest_task = asyncio.create_task(_collect(stream))

    await asyncio.sleep(0.7)
    await store.append(
        ProgressEventView(
            event_id="evt_done",
            run_id=RunId("run_slow"),
            sequence=2,
            kind=ProgressKind.COMPLETED,
            payload={},
            created_at=datetime.now(tz=UTC),
        )
    )
    rest = await rest_task
    assert any(frame == ": ping\n\n" for frame in rest)
    assert isinstance(rest[-1], ProgressEventView)
    assert rest[-1].kind is ProgressKind.STREAM_CLOSED
    assert rest[-1].payload == {"reason": "run.completed"}


async def test_idle_close_is_explicit_and_heartbeats_are_visible() -> None:
    from simulation_orchestration.application.values import ProgressKind
    from simulation_orchestration.infrastructure.memory import InMemoryProgressStore

    store = InMemoryProgressStore()
    await store.append(
        ProgressEventView(
            event_id="evt_start",
            run_id=RunId("run_idle"),
            sequence=1,
            kind=ProgressKind.PAUSED,
            payload={},
            created_at=datetime.now(tz=UTC),
        )
    )
    frames = [
        frame
        async for frame in StreamSimulationProgress(
            progress=store, idle_timeout_s=0.12, heartbeat_s=0.03
        ).execute(StreamSimulationProgressRequest(run_id=RunId("run_idle")))
    ]

    assert ": ping\n\n" in frames
    assert isinstance(frames[-1], ProgressEventView)
    assert frames[-1].kind is ProgressKind.STREAM_CLOSED
    assert frames[-1].payload == {"reason": "max_idle"}


async def test_disconnect_stops_polling_and_is_counted() -> None:
    from shared.metrics import METRICS
    from simulation_orchestration.application.values import ProgressKind
    from simulation_orchestration.infrastructure.memory import InMemoryProgressStore

    class _CountingStore(InMemoryProgressStore):
        def __init__(self) -> None:
            super().__init__()
            self.polls = 0

        async def list_after(
            self, run_id: RunId, after_sequence: int, limit: int
        ) -> list[ProgressEventView]:
            self.polls += 1
            return await super().list_after(run_id, after_sequence, limit)

    store = _CountingStore()
    await store.append(
        ProgressEventView(
            event_id="evt_start",
            run_id=RunId("run_gone"),
            sequence=1,
            kind=ProgressKind.STARTED,
            payload={},
            created_at=datetime.now(tz=UTC),
        )
    )
    before = METRICS.value("simulation_stream_disconnects_total")
    stream = cast(
        AsyncGenerator[ProgressEventView | str, None],
        StreamSimulationProgress(progress=store, idle_timeout_s=10.0, heartbeat_s=0.02).execute(
            StreamSimulationProgressRequest(run_id=RunId("run_gone"))
        ),
    )
    assert not isinstance(await anext(stream), str)
    await stream.aclose()
    polls = store.polls
    await asyncio.sleep(0.15)

    assert store.polls == polls
    assert METRICS.value("simulation_stream_disconnects_total") == before + 1
