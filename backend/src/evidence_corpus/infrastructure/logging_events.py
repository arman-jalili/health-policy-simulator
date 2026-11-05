"""In-process event publisher selected by ``PERSISTENCE=memory``.

Canonical: .pi/architecture/decisions/ADR-003-cross-context-communication.md

Events are emitted as structured log lines and retained for inspection in tests. PostgreSQL mode
uses the outbox adapter (`infrastructure/events.py`) instead; no use case changes.
"""

from __future__ import annotations

from collections.abc import Sequence

from evidence_corpus.domain.events import DomainEvent
from shared.log_setup import get_logger
from shared.metrics import METRICS

logger = get_logger(__name__)


class LoggingEventPublisher:
    """Publishes domain events as structured log lines and keeps them for inspection/tests."""

    def __init__(self) -> None:
        self.published: list[DomainEvent] = []

    async def publish(
        self,
        events: Sequence[DomainEvent],
        *,
        actor: str,
        trace_id: str | None = None,
    ) -> None:
        for event in events:
            self.published.append(event)
            METRICS.increment("domain_events_total", {"event": event.name})
            logger.info("domain_event", event_name=event.name, actor=actor)
