"""Audit trail for refusals and privileged actions (``shared_audit``).

The prototype must be able to answer "who did this, and was it allowed" for corpus ingestion,
brief publication and every guard rejection. Audit rows are append-only: no updates, no deletes.

Canonical: .pi/architecture/decisions/ADR-005-authentication-authorization.md (attribution)
"""

from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, Index, String, func, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column

from shared.clock import Clock, SystemClock
from shared.db import Base
from shared.enums import AuditOutcome
from shared.ids import new_id

AUDIT_ID_PREFIX = "aud"


class AuditRecord(Base):
    """Persisted row of ``shared_audit``; append-only."""

    __tablename__ = "shared_audit"
    __table_args__ = (
        Index("ix_shared_audit_occurred_at", "occurred_at"),
        Index("ix_shared_audit_resource_type_resource_id", "resource_type", "resource_id"),
        Index("ix_shared_audit_action", "action"),
    )

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    actor: Mapped[str] = mapped_column(String(120), nullable=False)
    action: Mapped[str] = mapped_column(String(120), nullable=False)
    resource_type: Mapped[str] = mapped_column(String(80), nullable=False)
    resource_id: Mapped[str | None] = mapped_column(String(120), nullable=True)
    outcome: Mapped[str] = mapped_column(
        String(16), nullable=False, server_default=text("'success'")
    )
    details: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, server_default=text("'{}'::jsonb")
    )
    trace_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    def __repr__(self) -> str:  # pragma: no cover - diagnostics only
        return f"AuditRecord(id={self.id!r}, action={self.action!r}, outcome={self.outcome!r})"


class AuditWriter:
    """Adds audit rows to a caller-owned transaction."""

    def __init__(self, clock: Clock | None = None) -> None:
        self._clock = clock or SystemClock()

    async def record(
        self,
        session: AsyncSession,
        *,
        action: str,
        actor: str,
        resource_type: str,
        resource_id: str | None = None,
        outcome: AuditOutcome = AuditOutcome.SUCCESS,
        details: Mapping[str, Any] | None = None,
        trace_id: str | None = None,
    ) -> AuditRecord:
        row = AuditRecord(
            id=new_id(AUDIT_ID_PREFIX),
            occurred_at=self._clock.now(),
            actor=actor,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            outcome=str(outcome),
            details=dict(details or {}),
            trace_id=trace_id,
        )
        session.add(row)
        return row
