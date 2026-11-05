"""Outbox-backed event publisher (ADR-003: events leave through the transactional outbox).

Canonical: .pi/architecture/decisions/ADR-003-cross-context-communication.md
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import asdict

from evidence_corpus.domain.events import DomainEvent
from shared.db import UnitOfWork
from shared.outbox import OutboxWriter


class OutboxEventPublisher:
    """Writes every drained domain event to ``shared_event_outbox``.

    The writer joins the ambient unit of work, so the row and the aggregate state change commit in
    the same transaction (ADR-002). Outside a request it opens its own transaction.
    """

    def __init__(self, unit_of_work: UnitOfWork, writer: OutboxWriter | None = None) -> None:
        self._uow = unit_of_work
        self._writer = writer or OutboxWriter()

    async def publish(
        self,
        events: Sequence[DomainEvent],
        *,
        actor: str,
        trace_id: str | None = None,
    ) -> None:
        if not events:
            return
        async with self._uow.session() as session:
            for event in events:
                await self._writer.write(
                    session,
                    event_name=event.name,
                    aggregate_type="EvidenceCorpus",
                    aggregate_id=self._aggregate_id(event),
                    payload=asdict(event),
                    actor=actor,
                    trace_id=trace_id,
                )

    @staticmethod
    def _aggregate_id(event: DomainEvent) -> str:
        for attribute in ("document_id", "article_id", "passage_id", "run_id", "snapshot_id"):
            value = getattr(event, attribute, None)
            if isinstance(value, str):
                return value
        raise ValueError(f"event {event.name} carries no aggregate id")


class RecordingEventPublisher:
    """Test double that records events without a database."""

    def __init__(self) -> None:
        self.events: list[DomainEvent] = []
        self.actors: list[str] = []

    async def publish(
        self,
        events: Sequence[DomainEvent],
        *,
        actor: str,
        trace_id: str | None = None,
    ) -> None:
        self.events.extend(events)
        self.actors.extend([actor] * len(events))
