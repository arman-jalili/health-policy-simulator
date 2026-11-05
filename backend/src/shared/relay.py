"""Transactional-outbox relay (ADR-002, ADR-003).

Canonical: .pi/architecture/decisions/ADR-003-cross-context-communication.md

The write side lives in :mod:`shared.outbox`; this module owns dispatch. A row is claimed with
``FOR UPDATE SKIP LOCKED``, handed to the in-process subscribers, and marked ``dispatched`` in the
same transaction. Running the poller twice therefore dispatches each row once.

Delivery is at-least-once: a crash between the subscriber call and the commit re-delivers the row.
Subscribers must key on ``event_id`` when their effect is not naturally idempotent — the contract
is stated on :class:`OutboxEvent`, not hidden in the relay.
"""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from datetime import datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from shared.clock import Clock, SystemClock
from shared.enums import OutboxStatus
from shared.log_setup import get_logger
from shared.outbox import OutboxEvent, OutboxMessage

logger = get_logger(__name__)

Subscriber = Callable[[OutboxEvent], Awaitable[None]]
WILDCARD = "*"


class OutboxRelay:
    """Drains pending outbox rows and dispatches them to in-process subscribers."""

    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        *,
        batch_size: int = 100,
        poll_interval_s: float = 1.0,
        max_attempts: int = 5,
        retry_backoff_s: float = 30.0,
        clock: Clock | None = None,
    ) -> None:
        self._session_factory = session_factory
        self._batch_size = batch_size
        self._poll_interval_s = poll_interval_s
        self._max_attempts = max_attempts
        self._retry_backoff_s = retry_backoff_s
        self._clock = clock or SystemClock()
        self._subscribers: dict[str, list[Subscriber]] = {}

    def subscribe(self, event_name: str, handler: Subscriber) -> None:
        """Register a handler for one event name, or ``"*"`` for every event."""
        self._subscribers.setdefault(event_name, []).append(handler)

    async def dispatch_once(self) -> int:
        """Dispatch one batch; returns the number of rows successfully delivered."""
        now = self._clock.now()
        async with self._session_factory() as session:
            statement = (
                select(OutboxMessage)
                .where(
                    OutboxMessage.status == OutboxStatus.PENDING.value,
                    OutboxMessage.available_at <= func.now(),
                )
                .order_by(OutboxMessage.sequence)
                .limit(self._batch_size)
                .with_for_update(skip_locked=True)
            )
            rows = list(await session.scalars(statement))
            dispatched = 0
            for row in rows:
                event = _to_event(row)
                try:
                    await self._deliver(event)
                except Exception as error:
                    self._record_failure(row, error, now)
                else:
                    row.status = OutboxStatus.DISPATCHED.value
                    row.dispatched_at = now
                    row.last_error = None
                    dispatched += 1
            await session.commit()
        if dispatched:
            logger.info("outbox_dispatched", count=dispatched)
        return dispatched

    async def run(self) -> None:
        """Poll forever; cancelled by the application lifespan on shutdown."""
        while True:
            try:
                await self.dispatch_once()
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.exception("outbox_relay_dispatch_failed")
            await asyncio.sleep(self._poll_interval_s)

    async def _deliver(self, event: OutboxEvent) -> None:
        handlers = [
            *self._subscribers.get(event.event_name, ()),
            *self._subscribers.get(WILDCARD, ()),
        ]
        if not handlers:
            logger.debug("outbox_event_unsubscribed", event_name=event.event_name)
            return
        for handler in handlers:
            await handler(event)

    def _record_failure(self, row: OutboxMessage, error: Exception, now: datetime) -> None:
        row.attempts += 1
        row.last_error = f"{type(error).__name__}: {error}"[:2000]
        if row.attempts >= self._max_attempts:
            row.status = OutboxStatus.FAILED.value
            logger.error(
                "outbox_event_failed",
                event_name=row.event_name,
                event_id=row.id,
                attempts=row.attempts,
            )
            return
        row.status = OutboxStatus.PENDING.value
        row.available_at = now + timedelta(seconds=self._retry_backoff_s * row.attempts)
        logger.warning(
            "outbox_event_retry_scheduled",
            event_name=row.event_name,
            event_id=row.id,
            attempts=row.attempts,
        )


def _to_event(row: OutboxMessage) -> OutboxEvent:
    return OutboxEvent(
        event_name=row.event_name,
        aggregate_type=row.aggregate_type,
        aggregate_id=row.aggregate_id,
        payload=dict(row.payload),
        actor=row.actor,
        occurred_at=row.occurred_at,
        trace_id=row.trace_id,
        payload_schema_version=row.payload_schema_version,
        event_id=row.id,
    )
