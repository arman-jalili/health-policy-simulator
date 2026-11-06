"""In-memory adapters for the frozen ports (issues #296, #299).

The append-only log allocates gap-free per-run ordinals itself (W9); application code never
derives ``count + 1``. These adapters keep unit tests hermetic and are the memory family of the
composition root.
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC, datetime

from negotiation_session.domain.events import DomainEvent, LoggedEvent
from negotiation_session.domain.repositories import (
    RunEventLog,
    SimulationRunRepository,
)
from negotiation_session.domain.simulation_run import SimulationRun
from negotiation_session.domain.values import RunId


class InMemorySimulationRunRepository:
    """Aggregate store keyed by run id; ``save`` writes the aggregate as-is."""

    def __init__(self) -> None:
        self._runs: dict[RunId, SimulationRun] = {}

    async def get(self, run_id: RunId) -> SimulationRun | None:
        return self._runs.get(run_id)

    async def all_ids(self) -> Sequence[RunId]:
        return tuple(self._runs)

    async def save(self, run: SimulationRun) -> None:
        self._runs[run.id] = run


class InMemoryRunEventLog:
    """Append-only run log with atomic per-run ordinals and round-bounded reads."""

    def __init__(self) -> None:
        self._events: dict[RunId, list[LoggedEvent]] = {}

    async def append(self, run_id: RunId, events: Sequence[DomainEvent]) -> Sequence[LoggedEvent]:
        stored = self._events.setdefault(run_id, [])
        start = len(stored) + 1
        logged = [
            LoggedEvent(sequence=start + index, event=event, occurred_at=datetime.now(tz=UTC))
            for index, event in enumerate(events)
        ]
        stored.extend(logged)
        return logged

    async def read(self, run_id: RunId, until_round: int | None = None) -> Sequence[LoggedEvent]:
        stored = self._events.get(run_id, [])
        if until_round is None:
            return list(stored)
        bounded: list[LoggedEvent] = []
        for logged in stored:
            round_number = getattr(logged.event, "round", None)
            if round_number is None:
                round_number = getattr(logged.event, "rounds", None)
            if round_number is None or int(round_number) <= until_round:
                bounded.append(logged)
        return bounded

    async def latest_sequence(self, run_id: RunId) -> int:
        return len(self._events.get(run_id, []))


__all__ = [
    "InMemoryRunEventLog",
    "InMemorySimulationRunRepository",
    "RunEventLog",
    "SimulationRunRepository",
]
