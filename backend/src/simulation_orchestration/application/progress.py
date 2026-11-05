"""Shared progress-event publisher (issue #216)."""

from __future__ import annotations

from dataclasses import asdict
from typing import Any, cast

from shared.ids import new_id
from shared.metrics import METRICS
from simulation_orchestration.application.dto import ProgressEventView
from simulation_orchestration.application.events import SimulationEvent
from simulation_orchestration.application.ports import Clock
from simulation_orchestration.application.repositories import ProgressStore
from simulation_orchestration.application.values import ProgressKind, RunId


class ProgressPublisher:
    def __init__(self, progress: ProgressStore, clock: Clock) -> None:
        self._progress = progress
        self._clock = clock

    async def publish(
        self, run_id: RunId, kind: ProgressKind, event: SimulationEvent
    ) -> ProgressEventView:
        sequence = await self._progress.latest_sequence(run_id) + 1
        METRICS.increment("simulation_progress_events_total", {"kind": kind.value})
        view = ProgressEventView(
            event_id=new_id("evt"),
            run_id=run_id,
            sequence=sequence,
            kind=kind,
            payload=asdict(cast(Any, event)),
            created_at=self._clock.now(),
        )
        return await self._progress.append(view)
