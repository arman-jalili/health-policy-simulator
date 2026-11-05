"""SQLAlchemy models for ClaimValidation (issue #179)."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import Date, DateTime, Numeric, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from shared.db import Base


class ClaimRow(Base):
    __tablename__ = "claim_validation_claim"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    claim_type: Mapped[str] = mapped_column(String(32), nullable=False)
    measure_key: Mapped[str | None] = mapped_column(String(512), nullable=True)
    measure: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    verdict: Mapped[str] = mapped_column(String(32), nullable=False)
    verification: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    review: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class ReferenceFigureRow(Base):
    __tablename__ = "claim_validation_reference_figure"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    measure_key: Mapped[str] = mapped_column(String(512), nullable=False, index=True)
    measure: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    value: Mapped[Decimal] = mapped_column(Numeric(24, 6), nullable=False)
    tier: Mapped[str] = mapped_column(String(64), nullable=False)
    as_of: Mapped[date] = mapped_column(Date, nullable=False)
    source_id: Mapped[str] = mapped_column(String(128), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class ContradictionRow(Base):
    __tablename__ = "claim_validation_contradiction"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    claim_id_a: Mapped[str] = mapped_column(String(64), nullable=False)
    claim_id_b: Mapped[str] = mapped_column(String(64), nullable=False)
    measure: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    delta: Mapped[Decimal] = mapped_column(Numeric(24, 6), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
