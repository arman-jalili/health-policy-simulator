"""Repository implementation boundary (contract frozen, issue #282).

The protocols are declared in ``domain/repositories.py`` so application code never imports
infrastructure. This module is the import point for adapters and the proofing check; it also
names the outbox writer the repository uses in the same transaction.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol, runtime_checkable

from negotiation_session.domain.events import DomainEvent
from negotiation_session.domain.repositories import RunEventLog, SimulationRunRepository
from negotiation_session.domain.values import RunId


@runtime_checkable
class OutboxWriter(Protocol):
    """Technical port: stage events for the shared outbox inside the current transaction."""

    async def write(self, run_id: RunId, events: Sequence[DomainEvent]) -> None: ...


__all__ = ["OutboxWriter", "RunEventLog", "SimulationRunRepository"]
