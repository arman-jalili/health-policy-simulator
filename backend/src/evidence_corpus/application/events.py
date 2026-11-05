"""Event publication port of the EvidenceCorpus application layer.

Canonical: .pi/architecture/modules/evidence-corpus.md

Use cases publish the events an aggregate drained; they never write the outbox themselves. The
adapter in `infrastructure/events.py` writes them into the transaction that saved the aggregate
(ADR-002/ADR-003).
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol, runtime_checkable

from evidence_corpus.domain.events import DomainEvent


@runtime_checkable
class EventPublisher(Protocol):
    async def publish(
        self,
        events: Sequence[DomainEvent],
        *,
        actor: str,
        trace_id: str | None = None,
    ) -> None:
        """Persist the events in the current unit of work; never swallow a failure."""
        ...
