"""Contract freeze: SSE ordering (issue #205)."""

from __future__ import annotations

import inspect

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


async def test_stream_replays_in_monotonic_order() -> None:
    store = await _seeded()
    service = StreamSimulationProgress(progress=store)

    events = [
        event
        async for event in service.execute(StreamSimulationProgressRequest(run_id=RunId("run_1")))
    ]

    assert [event.sequence for event in events] == [1, 2, 3]


async def test_last_event_id_replays_without_gaps_or_duplicates() -> None:
    store = await _seeded()
    service = StreamSimulationProgress(progress=store)

    events = [
        event
        async for event in service.execute(
            StreamSimulationProgressRequest(run_id=RunId("run_1"), last_event_id="evt_1")
        )
    ]

    assert [event.sequence for event in events] == [2, 3]


async def test_batching_preserves_order() -> None:
    store = await _seeded(5)
    service = StreamSimulationProgress(progress=store)

    events = [
        event
        async for event in service.execute(
            StreamSimulationProgressRequest(run_id=RunId("run_1"), limit=2)
        )
    ]

    assert [event.sequence for event in events] == [1, 2, 3, 4, 5]


async def test_unknown_last_event_id_is_rejected() -> None:
    store = await _seeded()
    service = StreamSimulationProgress(progress=store)

    with pytest.raises(ValueError, match="unknown Last-Event-ID"):
        [
            event
            async for event in service.execute(
                StreamSimulationProgressRequest(run_id=RunId("run_1"), last_event_id="evt_missing")
            )
        ]


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
