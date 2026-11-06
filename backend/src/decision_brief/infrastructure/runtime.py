"""Small runtime adapters of DecisionBrief (issue #345).

Clock, identifiers, unit of work and the event publisher are process-level concerns, not domain
ones. The event publisher only records events on the aggregate today; the outbox binding is the
runtime-integration issue's work, so this adapter logs what would be published instead of dropping
it silently.
"""

from __future__ import annotations

import dataclasses
from collections.abc import AsyncIterator, Sequence
from contextlib import asynccontextmanager
from decimal import Decimal
from enum import Enum
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from decision_brief.domain.events import DomainEvent
from shared.ids import new_id
from shared.log_setup import get_logger
from shared.outbox import OutboxWriter

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
    """In-memory publisher; the event is observable in logs and never dropped silently."""

    async def publish(self, events: Sequence[DomainEvent], *, trace_id: str | None = None) -> None:
        for event in events:
            logger.info(
                "decision_brief_event",
                event_name=type(event).__name__,
                trace_id=trace_id,
            )


def _scalar(value: Any) -> Any:
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, Decimal):
        return str(value)
    if dataclasses.is_dataclass(value):
        return {
            field.name: _scalar(getattr(value, field.name)) for field in dataclasses.fields(value)
        }
    if isinstance(value, (list, tuple)):
        return [_scalar(item) for item in value]
    if isinstance(value, dict):
        return {str(key): _scalar(item) for key, item in value.items()}
    return str(value) if value is not None else None


class SharedOutboxEventPublisher:
    """Write decision-brief events to ``shared_event_outbox`` (W4)."""

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory
        self._writer = OutboxWriter()

    async def publish(self, events: Sequence[DomainEvent], *, trace_id: str | None = None) -> None:
        if not events:
            return
        async with self._session_factory() as session:
            for event in events:
                payload = _scalar(event)
                aggregate_id = str(
                    getattr(event, "brief_id", None) or getattr(event, "run_id", "unknown")
                )
                await self._writer.write(
                    session,
                    event_name=type(event).__name__,
                    aggregate_type="DecisionBrief",
                    aggregate_id=aggregate_id,
                    payload=payload,
                    actor="decision_brief",
                    trace_id=trace_id,
                )
            await session.commit()
