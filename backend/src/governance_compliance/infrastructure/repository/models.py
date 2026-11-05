"""SQLAlchemy models for GovernanceCompliance (append-only audit tables)."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from shared.db import Base


class ViolationRow(Base):
    __tablename__ = "governance_compliance_violation"
    __table_args__ = (UniqueConstraint("violation_hash", name="uq_governance_violation_hash"),)

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    run_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    invocation_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    violation_class: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    offending_span: Mapped[str] = mapped_column(Text, nullable=False)
    rewritten_span: Mapped[str | None] = mapped_column(Text, nullable=True)
    rule_id: Mapped[str] = mapped_column(String(32), nullable=False)
    rule_version: Mapped[str] = mapped_column(String(128), nullable=False)
    violation_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    detected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class ProvenanceRow(Base):
    __tablename__ = "governance_compliance_provenance"
    __table_args__ = (
        UniqueConstraint("position_id", "version", name="uq_governance_provenance_version"),
    )

    position_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    version: Mapped[int] = mapped_column(Integer, primary_key=True)
    evidence_ids: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
    argument_ids: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
    invocation_id: Mapped[str] = mapped_column(String(64), nullable=False)
    prompt_version: Mapped[str] = mapped_column(String(64), nullable=False)
    model: Mapped[str] = mapped_column(String(128), nullable=False)
    disclosed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class AllowlistRow(Base):
    __tablename__ = "governance_compliance_allowlist"

    code: Mapped[str] = mapped_column(String(64), primary_key=True)
    canonical_name: Mapped[str] = mapped_column(Text, nullable=False)
    short_name: Mapped[str] = mapped_column(String(128), nullable=False)
    category: Mapped[str] = mapped_column(String(64), nullable=False)
    aliases: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    version: Mapped[str] = mapped_column(String(32), nullable=False, server_default="v1")
    loaded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
