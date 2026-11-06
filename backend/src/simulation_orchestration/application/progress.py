"""Shared progress-event publisher (issue #216)."""

from __future__ import annotations

import json
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
        METRICS.increment("simulation_progress_events_total", {"kind": kind.value})
        view = ProgressEventView(
            event_id=new_id("evt"),
            run_id=run_id,
            sequence=0,
            kind=kind,
            payload=_json_safe(asdict(cast(Any, event))),
            created_at=self._clock.now(),
        )
        return await self._progress.append(view)


def _json_safe(payload: dict[str, Any]) -> dict[str, Any]:
    """Round-trip through JSON so the persisted payload never carries a non-JSON type.

    Events carry ``Decimal`` values (``cost_estimate``, budget limits, the checkpoint's
    ``budget_used_cost``). The progress row is a JSON column, so a Decimal aborts the insert and the
    worker dead-letters the run — observed with non-zero model prices, i.e. on the first paid call
    ("Object of type Decimal is not JSON serializable"). ``default=str`` keeps the value
    lossless as a decimal string, which is how the API renders money anyway.
    """
    return cast(dict[str, Any], json.loads(json.dumps(payload, default=str, sort_keys=False)))
