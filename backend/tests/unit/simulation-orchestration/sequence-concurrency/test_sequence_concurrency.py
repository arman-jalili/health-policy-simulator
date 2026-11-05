"""Concurrent progress allocation: no read-then-write race, no lost events (#238)."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime

from simulation_orchestration.application.commands import StreamSimulationProgressRequest
from simulation_orchestration.application.events import RunStarted
from simulation_orchestration.application.progress import ProgressPublisher
from simulation_orchestration.application.services import StreamSimulationProgress
from simulation_orchestration.application.values import JobId, ProgressKind, RunId
from simulation_orchestration.infrastructure.memory import InMemoryProgressStore


class _Clock:
    def now(self) -> datetime:
        return datetime(2026, 11, 6, tzinfo=UTC)


async def _publish_many(store: InMemoryProgressStore, count: int) -> None:
    publisher = ProgressPublisher(store, _Clock())
    await asyncio.gather(
        *(
            publisher.publish(
                RunId("run_1"),
                ProgressKind.STARTED,
                RunStarted(job_id=JobId("job_1"), run_id=RunId("run_1")),
            )
            for _ in range(count)
        )
    )


async def test_ten_concurrent_publishes_produce_a_gapless_stream() -> None:
    store = InMemoryProgressStore()

    await _publish_many(store, 10)

    events = await store.list_after(RunId("run_1"), 0, 100)
    assert [event.sequence for event in events] == list(range(1, 11))
    assert len({event.event_id for event in events}) == 10
    assert await store.latest_sequence(RunId("run_1")) == 10


async def test_sse_replay_after_last_event_id_returns_each_event_once() -> None:
    store = InMemoryProgressStore()
    await _publish_many(store, 10)
    all_events = await store.list_after(RunId("run_1"), 0, 100)
    service = StreamSimulationProgress(progress=store)

    replay = [
        event
        async for event in service.execute(
            StreamSimulationProgressRequest(
                run_id=RunId("run_1"), last_event_id=all_events[4].event_id
            )
        )
    ]

    assert [event.sequence for event in replay] == [6, 7, 8, 9, 10]
    assert len({event.event_id for event in replay}) == len(replay)
