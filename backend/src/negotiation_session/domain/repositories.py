"""Domain-owned repository ports (contract frozen, issue #282).

Canonical: ``.pi/architecture/modules/negotiation-session.md`` (Domain-owned repositories)

``save`` writes the aggregate and its outbox rows in one transaction. ``RunEventLog`` is
append-only and allocates the per-run ordinal itself (W9), never ``count + 1`` in use-case
code. Database columns are out of scope: they are hidden behind these ports (ADR-002).
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol, runtime_checkable

from negotiation_session.domain.events import DomainEvent, LoggedEvent
from negotiation_session.domain.simulation_run import SimulationRun
from negotiation_session.domain.values import RunId


@runtime_checkable
class SimulationRunRepository(Protocol):
    """Persistence boundary of the one aggregate root."""

    async def get(self, run_id: RunId) -> SimulationRun | None: ...

    async def save(self, run: SimulationRun) -> None:
        """Persist the run and append its drained events in the same transaction."""
        ...


@runtime_checkable
class RunEventLog(Protocol):
    """Append-only run log that ``ReplaySimulationHistory`` folds (AC 11)."""

    async def append(self, run_id: RunId, events: Sequence[DomainEvent]) -> Sequence[LoggedEvent]:
        """Append events, allocating gap-free per-run ordinals atomically."""
        ...

    async def read(self, run_id: RunId, until_round: int | None = None) -> Sequence[LoggedEvent]:
        """Read ordered events; ``until_round`` bounds the fold by round number."""
        ...

    async def latest_sequence(self, run_id: RunId) -> int: ...
