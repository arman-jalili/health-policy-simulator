"""Persistence model for frozen evidence packs.

Canonical: .pi/architecture/modules/evidence-retrieval.md

The payload is JSONB so the aggregate's shape stays owned by the domain; the table is an adapter
detail. `claim` is duplicated for the latest-for-claim query without exposing candidate rows.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from shared.db import Base


class EvidencePackRow(Base):
    __tablename__ = "evidence_retrieval_pack"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    claim: Mapped[str] = mapped_column(String(2000), nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
