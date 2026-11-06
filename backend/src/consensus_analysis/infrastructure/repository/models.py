"""ORM mapping for consensus projection rows (issue #406)."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, Integer, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from shared.db import Base


class ConsensusRecordRow(Base):
    __tablename__ = "consensus_analysis_consensus_record"
    __table_args__ = (UniqueConstraint("run_id", "topic", name="uq_consensus_analysis_run_topic"),)

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    run_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    topic: Mapped[str] = mapped_column(String(512), nullable=False)
    log_position: Mapped[int] = mapped_column(Integer, nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
