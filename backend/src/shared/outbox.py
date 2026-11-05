"""Transactional outbox: the only way a context announces a domain event (ADR-002, ADR-003).

The row is written in the same transaction as the state change, so an event can never be
lost and a state change can never be published twice by accident. Dispatch (the relay) is a
separate concern; this module owns the write side and the persisted row shape.

Canonical: .pi/architecture/decisions/ADR-003-cross-context-communication.md
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from sqlalchemy import BigInteger, DateTime, Identity, Index, Integer, String, Text, func, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column

from shared.clock import Clock, SystemClock
from shared.db import Base
from shared.enums import OutboxStatus
from shared.ids import new_id

EVENT_ID_PREFIX = "evt"


@dataclass(frozen=True, slots=True)
class OutboxEvent:
    """An immutable fact published by a bounded context."""

    event_name: str
    aggregate_type: str
    aggregate_id: str
    payload: Mapping[str, Any]
    actor: str
    occurred_at: datetime
    trace_id: str | None = None
    payload_schema_version: int = 1
    event_id: str = field(default_factory=lambda: new_id(EVENT_ID_PREFIX))

    def __post_init__(self) -> None:
        if not self.event_name:
            raise ValueError("event_name must not be empty")
        if not self.actor.strip():
            raise ValueError("actor must not be empty")
        if self.occurred_at.tzinfo is None:
            raise ValueError("occurred_at must be timezone-aware")
        try:
            json.dumps(dict(self.payload), allow_nan=False)
        except (TypeError, ValueError) as error:
            raise ValueError(f"event payload is not JSON-serialisable: {error}") from error


class OutboxMessage(Base):
    """Persisted row of ``shared_event_outbox``."""

    __tablename__ = "shared_event_outbox"
    __table_args__ = (
        Index("ix_shared_event_outbox_status_available_at", "status", "available_at"),
        Index(
            "ix_shared_event_outbox_aggregate_type_aggregate_id",
            "aggregate_type",
            "aggregate_id",
        ),
    )

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    sequence: Mapped[int] = mapped_column(
        BigInteger, Identity(always=True), nullable=False, unique=True
    )
    event_name: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    aggregate_type: Mapped[str] = mapped_column(String(80), nullable=False)
    aggregate_id: Mapped[str] = mapped_column(String(120), nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    payload_schema_version: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default=text("1")
    )
    actor: Mapped[str] = mapped_column(String(120), nullable=False)
    trace_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    status: Mapped[str] = mapped_column(
        String(16), nullable=False, server_default=text("'pending'")
    )
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    available_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    dispatched_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)

    def __repr__(self) -> str:  # pragma: no cover - diagnostics only
        return f"OutboxMessage(id={self.id!r}, event_name={self.event_name!r})"


class OutboxWriter:
    """Adds outbox rows to a caller-owned transaction. Never commits, never flushes."""

    def __init__(self, clock: Clock | None = None) -> None:
        self._clock = clock or SystemClock()

    def build(
        self,
        *,
        event_name: str,
        aggregate_type: str,
        aggregate_id: str,
        payload: Mapping[str, Any],
        actor: str,
        trace_id: str | None = None,
        payload_schema_version: int = 1,
    ) -> OutboxEvent:
        return OutboxEvent(
            event_name=event_name,
            aggregate_type=aggregate_type,
            aggregate_id=aggregate_id,
            payload=dict(payload),
            actor=actor,
            trace_id=trace_id,
            payload_schema_version=payload_schema_version,
            occurred_at=self._clock.now(),
        )

    @staticmethod
    def to_row(event: OutboxEvent) -> OutboxMessage:
        return OutboxMessage(
            id=event.event_id,
            event_name=event.event_name,
            aggregate_type=event.aggregate_type,
            aggregate_id=event.aggregate_id,
            payload=dict(event.payload),
            payload_schema_version=event.payload_schema_version,
            actor=event.actor,
            trace_id=event.trace_id,
            occurred_at=event.occurred_at,
            status=OutboxStatus.PENDING.value,
        )

    async def write(
        self,
        session: AsyncSession,
        *,
        event_name: str,
        aggregate_type: str,
        aggregate_id: str,
        payload: Mapping[str, Any],
        actor: str,
        trace_id: str | None = None,
        payload_schema_version: int = 1,
    ) -> OutboxEvent:
        event = self.build(
            event_name=event_name,
            aggregate_type=aggregate_type,
            aggregate_id=aggregate_id,
            payload=payload,
            actor=actor,
            trace_id=trace_id,
            payload_schema_version=payload_schema_version,
        )
        session.add(self.to_row(event))
        return event
