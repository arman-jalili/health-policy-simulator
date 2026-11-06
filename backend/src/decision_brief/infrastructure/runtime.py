"""Small runtime adapters of DecisionBrief (issue #345).

Clock, identifiers, unit of work and the event publisher are process-level concerns, not domain
ones. The event publisher only records events on the aggregate today; the outbox binding is the
runtime-integration issue's work, so this adapter logs what would be published instead of dropping
it silently.
"""

from __future__ import annotations

from collections.abc import AsyncIterator, Sequence
from contextlib import asynccontextmanager

from decision_brief.domain.events import DomainEvent
from shared.ids import new_id
from shared.log_setup import get_logger

logger = get_logger(__name__)


class UuidFactory:
    """Prefixed ULID identifiers, as every other context uses."""

    def new_id(self, prefix: str) -> str:
        return new_id(prefix)


class NoopUnitOfWork:
    """In-memory family has no transaction to open; the interface still has to be satisfied."""

    @asynccontextmanager
    async def transaction(self) -> AsyncIterator[None]:
        yield None


class LoggingEventPublisher:
    """Make publication events observable until the shared outbox is bound."""

    async def publish(self, events: Sequence[DomainEvent], *, trace_id: str | None = None) -> None:
        for event in events:
            logger.info(
                "decision_brief_event",
                event_name=type(event).__name__,
                trace_id=trace_id,
            )
